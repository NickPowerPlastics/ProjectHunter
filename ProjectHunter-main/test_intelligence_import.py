import io
import json
import re
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import app as app_module
from app import app
from intelligence_store import (
    IntelligenceStore,
    IntelligenceValidationError,
    parse_intelligence_json,
    preview_intelligence_payload,
)


def feed(updated_at="2026-08-04", project_name="Alpha", contact_name="Avery"):
    return {
        "updated_at": updated_at,
        "projects": {
            "alpha": {"name": project_name, "state": "Arizona"},
            "beta": {"name": "Beta", "state": "Texas"},
        },
        "contacts": [{"name": contact_name, "email": "avery@example.com"}],
    }


class IntelligenceImportUnitTests(unittest.TestCase):
    def make_store(self, payload):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        path = Path(temporary_directory.name) / "data" / "intelligence.json"
        path.parent.mkdir()
        path.write_text(json.dumps(payload), encoding="utf-8")
        return IntelligenceStore(path)

    def test_schema_rejects_missing_feed_date(self):
        payload = feed()
        del payload["updated_at"]
        with self.assertRaisesRegex(IntelligenceValidationError, "updated_at"):
            parse_intelligence_json(json.dumps(payload))

    def test_preview_counts_states_projects_and_contacts(self):
        preview = preview_intelligence_payload(feed())
        self.assertEqual(preview["project_count"], 2)
        self.assertEqual(preview["contact_count"], 1)
        self.assertEqual(preview["state_count"], 2)
        self.assertEqual(preview["states"], [("Arizona", 1), ("Texas", 1)])
        self.assertEqual(preview["projects"], ["Alpha", "Beta"])
        self.assertEqual(preview["contacts"], ["Avery"])

    def test_replace_creates_backup_saves_and_reloads(self):
        original = feed("2026-08-01", project_name="Original")
        replacement = feed(project_name="Replacement")
        store = self.make_store(original)

        backup_path = store.replace(replacement)

        self.assertEqual(json.loads(backup_path.read_text(encoding="utf-8")), original)
        self.assertEqual(json.loads(store.path.read_text(encoding="utf-8")), replacement)
        self.assertEqual(store.snapshot()["projects"][0]["name"], "Replacement")
        self.assertIsNotNone(store.last_updated)

    def test_freshness_flags_feed_after_configured_window(self):
        store = self.make_store(feed("2026-07-31"))
        freshness = store.freshness(
            now=datetime(2026, 8, 4, tzinfo=timezone.utc), stale_after_days=3
        )
        self.assertTrue(freshness["is_stale"])
        self.assertEqual(freshness["age_days"], 4)


class IntelligenceAdminRouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        path = Path(self.temporary_directory.name) / "data" / "intelligence.json"
        path.parent.mkdir()
        path.write_text(json.dumps(feed("2026-08-01", project_name="Original")), encoding="utf-8")
        self.store = IntelligenceStore(path)
        self.store.reload()
        self.store_patch = patch.object(app_module, "intelligence_store", self.store)
        self.store_patch.start()
        self.addCleanup(self.store_patch.stop)

    def csrf_token(self):
        response = self.client.get("/admin/intelligence")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def test_admin_is_loopback_only(self):
        response = self.client.get("/admin/intelligence", environ_base={"REMOTE_ADDR": "192.0.2.10"})
        self.assertEqual(response.status_code, 403)

    def test_admin_rejects_post_without_csrf_token(self):
        response = self.client.post("/admin/intelligence", data={"json_text": json.dumps(feed())})
        self.assertEqual(response.status_code, 400)

    def test_mission_control_shows_feed_date_and_stale_warning(self):
        with patch.object(self.store, "freshness", return_value={
            "feed_date": "2026-08-01", "age_days": 4, "stale_after_days": 3, "is_stale": True,
        }):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Intelligence feed: 2026-08-01", response.data)
        self.assertIn(b"Stale feed warning", response.data)

    def test_upload_can_be_validated_and_previewed(self):
        token = self.csrf_token()
        response = self.client.post(
            "/admin/intelligence",
            data={
                "csrf_token": token,
                "action": "preview",
                "json_file": (io.BytesIO(json.dumps(feed()).encode()), "intelligence.json"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Schema valid", response.data)
        self.assertIn(b"Arizona", response.data)
        self.assertIn(b"Alpha", response.data)
        self.assertIn(b"Avery", response.data)

    def test_confirmed_import_backs_up_replaces_and_reloads(self):
        token = self.csrf_token()
        replacement = feed(project_name="Replacement")
        preview_response = self.client.post(
            "/admin/intelligence",
            data={"csrf_token": token, "action": "preview", "json_text": json.dumps(replacement)},
        )
        self.assertEqual(preview_response.status_code, 200)
        response = self.client.post(
            "/admin/intelligence",
            data={
                "csrf_token": token,
                "action": "import",
                "preview_confirmed": "1",
                "json_text": json.dumps(replacement),
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Imported 2 projects and 1 contacts", response.data)
        self.assertEqual(self.store.snapshot()["projects"][0]["name"], "Replacement")
        backups = list((self.store.path.parent / "backups").glob("intelligence-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertIn("Original", backups[0].read_text(encoding="utf-8"))

    def test_import_without_matching_preview_is_blocked(self):
        token = self.csrf_token()
        response = self.client.post(
            "/admin/intelligence",
            data={
                "csrf_token": token,
                "action": "import",
                "preview_confirmed": "1",
                "json_text": json.dumps(feed(project_name="Unpreviewed")),
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Preview and confirm", response.data)
        self.assertEqual(self.store.snapshot()["projects"][0]["name"], "Original")


if __name__ == "__main__":
    unittest.main()
