import unittest
from datetime import date, datetime, timezone

from dashboard_engine import (
    build_activity,
    build_follow_ups,
    build_priorities,
    calculate_revenue,
    relative_time,
)


class DashboardEngineTests(unittest.TestCase):
    def setUp(self):
        self.projects = [{
            "id": 1, "name": "Alpha", "developer": "Owner", "electrical_contractor": "Power Co",
            "current_stage": "Active Construction", "confidence": 80, "estimated_revenue": 100000,
            "last_activity": "2026-07-20", "recommended_next_action": "Call estimating", "timeline": [],
        }, {
            "id": 2, "name": "Beta", "developer": "Owner", "electrical_contractor": "",
            "current_stage": "Needs Research", "confidence": 30, "estimated_revenue": 50000,
            "last_activity": "2026-08-03", "recommended_next_action": "Identify contractor", "timeline": [],
        }]
        self.contacts = [{"name": "Alex", "company": "Power Co", "ready_to_email": True,
                          "outreach_status": "Email opened", "email_status": "Verified", "last_contacted": "2026-08-02"}]

    def test_priorities_are_ranked_and_bounded(self):
        priorities = build_priorities(self.projects, self.contacts)
        self.assertEqual(priorities[0]["name"], "Alpha")
        self.assertTrue(all(0 <= item["priority_score"] <= 100 for item in priorities))

    def test_follow_ups_derive_from_feed_and_can_be_dismissed(self):
        tasks = build_follow_ups(self.projects, self.contacts, today=date(2026, 8, 4))
        reasons = {task["reason"] for task in tasks}
        kinds = {task["kind"] for task in tasks}
        self.assertIn("No activity in 7 days", reasons)
        self.assertIn("Email opened but no reply", reasons)
        self.assertIn("Research incomplete", reasons)
        self.assertIn("research-incomplete", kinds)
        dismissed = {tasks[0]["id"]}
        self.assertNotIn(tasks[0]["id"], {task["id"] for task in build_follow_ups(self.projects, self.contacts, dismissed, date(2026, 8, 4))})

    def test_revenue_formulas_use_project_confidence(self):
        revenue = calculate_revenue(self.projects)
        self.assertEqual(revenue["potential"], 150000)
        self.assertEqual(revenue["weighted"], 95000)
        self.assertEqual(revenue["confidence"], 63)

    def test_activity_has_relative_times_and_workspace_targets(self):
        activity = build_activity(self.projects, self.contacts)
        self.assertIn("Contact imported", {event["type"] for event in activity})
        self.assertTrue(all("relative_time" in event for event in activity))
        self.assertEqual(relative_time("2026-08-03", datetime(2026, 8, 4, tzinfo=timezone.utc)), "yesterday")


if __name__ == "__main__":
    unittest.main()
