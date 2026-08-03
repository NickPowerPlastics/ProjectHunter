import unittest

from app import app
from intelligence_store import intelligence_store


class PlatformIntelligenceTests(unittest.TestCase):
    def setUp(self):
        intelligence_store.reload()
        self.client = app.test_client()

    def test_feed_contains_all_target_states_and_expected_counts(self):
        counts = {state["name"]: len(state["projects"]) for state in intelligence_store.states()}
        self.assertEqual(counts["Arizona"], 15)
        self.assertEqual(counts["Texas"], 4)
        self.assertTrue({"Virginia", "Kentucky", "Minnesota", "North Carolina", "New Jersey", "Ohio"} <= counts.keys())

    def test_dashboard_exposes_new_metrics_and_sections(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for label in (b"Projects", b"Companies", b"Contacts", b"States", b"Estimated Pipeline", b"Recent discoveries", b"Highest confidence opportunities", b"Projects needing research", b"Recently updated projects"):
            self.assertIn(label, response.data)

    def test_state_explorer_and_global_search(self):
        response = self.client.get("/projects")
        self.assertIn(b"Arizona", response.data)
        self.assertIn(b"Texas", response.data)
        self.assertIn(b"AWS Loudoun County expansion", response.data)
        response = self.client.get("/search?q=Rosendin")
        self.assertIn(b"Companies (1)", response.data)
        self.assertIn(b"Contacts (6)", response.data)

    def test_company_and_project_workspaces(self):
        company = next(item for item in intelligence_store.companies() if item["name"] == "Rosendin")
        response = self.client.get(f'/company/{company["id"]}')
        for label in (b"Estimated Opportunity", b"Last Activity", b"Contractor Confidence", b"Open Tasks"):
            self.assertIn(label, response.data)
        response = self.client.get("/project/3")
        for label in (b"Mechanical Contractor", b"Evidence", b"Recommended Next Action", b"Timeline", b"Estimated Revenue"):
            self.assertIn(label, response.data)


if __name__ == "__main__":
    unittest.main()
