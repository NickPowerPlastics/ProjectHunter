import json
import unittest
from pathlib import Path

from dashboard_engine import build_daily_actions
from intelligence_store import IntelligenceStore, validate_intelligence_payload


class DailyActionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path(__file__).resolve().parents[1] / "data" / "intelligence.json"
        cls.raw = json.loads(cls.path.read_text(encoding="utf-8"))
        cls.data = IntelligenceStore(cls.path).snapshot()

    def test_feed_and_hunt_opportunity_are_valid(self):
        validate_intelligence_payload(self.raw)
        hunt = [project for project in self.data["projects"] if "Hunt Electric" in project["name"]]
        self.assertEqual(len(hunt), 1)
        self.assertFalse(hunt[0]["electrical_contractor"])
        self.assertIn("unverified", hunt[0]["name"].lower())

    def test_daily_queue_has_unique_verified_email_actions(self):
        actions = build_daily_actions(self.data["projects"], self.data["contacts"])
        self.assertEqual(len(actions), 20)
        email_actions = [action for action in actions if action["kind"] == "email"]
        emails = [action["contact"]["email"] for action in email_actions]
        self.assertEqual(len(emails), len(set(emails)))
        self.assertTrue(all(action["contact"]["ready_to_email"] for action in email_actions))
        self.assertTrue(all(action["contact"]["email_status"] != "Bounced" for action in email_actions))

    def test_missing_contacts_become_research_actions(self):
        actions = build_daily_actions(self.data["projects"], self.data["contacts"], limit=100)
        hunt = next(action for action in actions if "Hunt Electric" in action["project"]["name"])
        self.assertEqual(hunt["kind"], "research-contractor")
        self.assertIsNone(hunt["contact"])


if __name__ == "__main__":
    unittest.main()
