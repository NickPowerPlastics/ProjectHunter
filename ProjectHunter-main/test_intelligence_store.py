import json
import tempfile
import unittest
from pathlib import Path

from intelligence_store import IntelligenceStore


class IntelligenceStoreTests(unittest.TestCase):
    def make_store(self, payload):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "intelligence.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return IntelligenceStore(path)

    def test_loads_json_projects_and_contacts(self):
        store = self.make_store({"projects": {"alpha": {"display_name": "Alpha"}}, "contacts": [{"email": "a@example.com"}]})
        data = store.reload()
        self.assertEqual(data["projects"][0]["display_name"], "Alpha")
        self.assertEqual(data["contacts"][0]["email"], "a@example.com")
        self.assertIsNotNone(store.last_updated)

    def test_deduplicates_contacts_by_case_insensitive_email(self):
        store = self.make_store({"projects": {}, "contacts": [
            {"name": "First", "email": "Person@Example.com", "priority": 20},
            {"name": "Duplicate", "email": "person@example.com", "priority": 99},
        ]})
        contacts = store.reload()["contacts"]
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]["name"], "First")

    def test_known_helix_bounces_are_excluded_from_ready_email(self):
        store = self.make_store({"projects": {}, "contacts": [{
            "name": "Rick", "company": "Helix Electric", "email": "r.measles@helixelectric.com", "email_status": "Verified"
        }]})
        contact = store.reload()["contacts"][0]
        self.assertEqual(contact["email_status"], "Bounced")
        self.assertFalse(contact["ready_to_email"])

    def test_dashboard_metrics_are_derived_from_normalized_data(self):
        store = self.make_store({"projects": {
            "confirmed": {"contractors": [{"trade": "Electrical contractor", "status": "Confirmed"}]},
            "research": {"contractors": [{"trade": "Candidate", "status": "Possible"}]},
        }, "contacts": [
            {"email": "verified@example.com", "email_status": "Verified", "priority": 95},
            {"email": "r.measles@helixelectric.com", "email_status": "Verified", "priority": 80},
        ]})
        store.reload()
        self.assertEqual(store.metrics(), {"total_projects": 2, "confirmed_contractors": 1,
            "projects_needing_research": 1, "total_contacts": 2, "verified_contacts": 1,
            "bounced_contacts": 1, "high_priority_contacts": 1})


if __name__ == "__main__":
    unittest.main()
