import json
import unittest
from pathlib import Path
from unittest.mock import patch

from app import app


class ProjectHunterAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home_page_renders_expected_content(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Project Hunter", response.data)
        self.assertIn(b"Today's Opportunities", response.data)
        self.assertIn(b"/static/style.css", response.data)

    def test_home_page_uses_projects_from_json_file(self):
        projects_path = Path(__file__).with_name("projects.json")
        with projects_path.open(encoding="utf-8") as handle:
            projects = json.load(handle)

        with patch("app.load_projects", return_value=projects):
            response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Microsoft Goodyear", response.data)
        self.assertIn(b"Data Centers", response.data)
        self.assertIn(b"/project/1", response.data)
        self.assertIn(b"Research needed", response.data)
        self.assertIn(b"Identify electrical contractor", response.data)

    def test_project_details_page_renders_project_fields(self):
        projects = [
            {
                "id": 1,
                "name": "Custom Project",
                "state": "Arizona",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "Example GC",
                "electrical_contractor": "Example EC",
                "status": "In Progress",
                "next_action": "Schedule site visit",
            }
        ]

        with patch("app.load_projects", return_value=projects):
            response = self.client.get("/project/1")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Custom Project", response.data)
        self.assertIn(b"Arizona", response.data)
        self.assertIn(b"Example Developer", response.data)
        self.assertIn(b"Back to Dashboard", response.data)
        self.assertIn(b"Edit Project", response.data)

    def test_project_details_page_includes_research_button(self):
        projects = [
            {
                "id": 1,
                "name": "Research Project",
                "state": "Arizona",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "Example GC",
                "electrical_contractor": "Example EC",
                "status": "In Progress",
                "next_action": "Schedule site visit",
            }
        ]

        with patch("app.load_projects", return_value=projects):
            response = self.client.get("/project/1")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Research", response.data)

    def test_research_page_renders_sections_and_placeholder_content(self):
        projects = [
            {
                "id": 1,
                "name": "Research Project",
                "state": "Arizona",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "Example GC",
                "electrical_contractor": "Example EC",
                "status": "In Progress",
                "next_action": "Schedule site visit",
            }
        ]

        with patch("app.load_projects", return_value=projects):
            response = self.client.get("/project/1/research")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Project Overview", response.data)
        self.assertIn(b"Developer", response.data)
        self.assertIn(b"General Contractor", response.data)
        self.assertIn(b"Electrical Contractor", response.data)
        self.assertIn(b"Civil Contractor", response.data)
        self.assertIn(b"Utility Company", response.data)
        self.assertIn(b"Project News", response.data)
        self.assertIn(b"Permit Information", response.data)
        self.assertIn(b"Apollo Contacts", response.data)
        self.assertIn(b"HubSpot Activity", response.data)
        self.assertIn(b"Method Quote History", response.data)
        self.assertIn(b"AI Notes", response.data)
        self.assertIn(b"Recommended Next Action", response.data)
        self.assertIn(b"No research available yet.", response.data)
        self.assertIn(b"Run Research", response.data)
        self.assertIn(b"Research providers coming soon.", response.data)

    def test_dashboard_renders_sidebar_navigation(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/projects", response.data)
        self.assertIn(b"/companies", response.data)
        self.assertIn(b"/contacts", response.data)
        self.assertIn(b"/tasks", response.data)
        self.assertIn(b'nav-link active', response.data)

    def test_projects_page_renders_with_active_nav(self):
        response = self.client.get("/projects")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Projects", response.data)
        self.assertIn(b'nav-link active', response.data)

    def test_dashboard_renders_favorites_section_and_orders_favorites_first(self):
        projects = [
            {
                "id": 1,
                "name": "Alpha Project",
                "state": "Arizona",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "",
                "electrical_contractor": "",
                "status": "In Progress",
                "next_action": "Continue",
                "score": 50,
                "favorite": False,
            },
            {
                "id": 2,
                "name": "Beta Project",
                "state": "Arizona",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "",
                "electrical_contractor": "",
                "status": "Needs Review",
                "next_action": "Follow up",
                "score": 90,
                "favorite": True,
            },
        ]

        with patch("app.load_projects", return_value=projects):
            response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Favorites", response.data)
        self.assertIn(b"Beta Project", response.data)

    def test_toggle_favorite_saves_state_and_redirects(self):
        projects = [
            {
                "id": 1,
                "name": "Alpha Project",
                "state": "Arizona",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "",
                "electrical_contractor": "",
                "status": "In Progress",
                "next_action": "Continue",
                "score": 50,
                "favorite": False,
            }
        ]

        with patch("app.load_projects", return_value=projects), patch("app.save_projects") as save_projects:
            response = self.client.post("/project/1/favorite", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        self.assertTrue(projects[0]["favorite"])
        save_projects.assert_called_once()

    def test_companies_page_renders_deduplicated_company_list(self):
        projects = [
            {
                "id": 1,
                "name": "Project One",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "Example GC",
                "electrical_contractor": "Example EC",
                "status": "In Progress",
                "next_action": "Continue",
            },
            {
                "id": 2,
                "name": "Project Two",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "Another GC",
                "electrical_contractor": "Example EC",
                "status": "Needs Review",
                "next_action": "Follow up",
            },
        ]

        with patch("app.load_projects", return_value=projects):
            response = self.client.get("/companies")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Example Developer", response.data)
        self.assertIn(b"Example EC", response.data)
        self.assertIn(b"Developer", response.data)
        self.assertIn(b"General Contractor", response.data)

    def test_company_details_page_renders_company_information(self):
        projects = [
            {
                "id": 1,
                "name": "Project One",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "",
                "electrical_contractor": "",
                "status": "In Progress",
                "next_action": "Continue",
            }
        ]

        with patch("app.load_projects", return_value=projects):
            response = self.client.get("/company/1")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Example Developer", response.data)
        self.assertIn(b"Apollo Contacts", response.data)
        self.assertIn(b"Project One", response.data)

    def test_discover_projects_page_renders_search_form_and_results(self):
        response = self.client.get("/discover?region=Arizona&market=Data%20Centers")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Discover Projects", response.data)
        self.assertIn(b"Search Region", response.data)
        self.assertIn(b"Data Centers", response.data)
        self.assertIn(b"West Valley", response.data)
        self.assertIn(b"Import", response.data)

    def test_run_discovery_generates_simulated_projects(self):
        response = self.client.post(
            "/discover/run",
            data={"region": "Arizona", "market": "Data Centers"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Discovery run complete", response.data)
        self.assertIn(b"Arizona Digital Campus", response.data)

    def test_import_discovered_project_saves_to_projects_and_prevents_duplicates(self):
        projects = [
            {
                "id": 1,
                "name": "Existing Project",
                "state": "Arizona",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "Example GC",
                "electrical_contractor": "Example EC",
                "status": "In Progress",
                "next_action": "Schedule site visit",
            }
        ]

        with patch("app.load_projects", return_value=projects), patch("app.save_projects") as save_projects:
            response = self.client.post(
                "/discover/import",
                data={"project_name": "West Valley Data Center", "region": "Arizona", "market": "Data Centers"},
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"imported successfully", response.data)
        save_projects.assert_called_once()

        with patch("app.load_projects", return_value=projects), patch("app.save_projects") as save_projects:
            response = self.client.post(
                "/discover/import",
                data={"project_name": "Existing Project", "region": "Arizona", "market": "Data Centers"},
                follow_redirects=True,
            )

        self.assertIn(b"already imported", response.data)
        save_projects.assert_not_called()

    def test_add_project_saves_new_project_and_redirects(self):
        projects = [
            {
                "id": 1,
                "name": "Existing Project",
                "state": "Arizona",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "Example GC",
                "electrical_contractor": "Example EC",
                "status": "In Progress",
                "next_action": "Schedule site visit",
            }
        ]

        with patch("app.load_projects", return_value=projects), patch("app.save_projects") as save_projects:
            response = self.client.post(
                "/project/add",
                data={
                    "name": "New Project",
                    "state": "Nevada",
                    "market": "Utilities",
                    "business_line": "Transmission",
                    "developer": "New Developer",
                    "general_contractor": "New GC",
                    "electrical_contractor": "New EC",
                    "status": "Planned",
                    "next_action": "Kickoff meeting",
                },
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        save_projects.assert_called_once()

    def test_edit_project_saves_changes_and_redirects(self):
        projects = [
            {
                "id": 1,
                "name": "Custom Project",
                "state": "Arizona",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "Example GC",
                "electrical_contractor": "Example EC",
                "status": "In Progress",
                "next_action": "Schedule site visit",
            }
        ]

        with patch("app.load_projects", return_value=projects), patch("app.save_projects") as save_projects:
            response = self.client.post(
                "/project/1/edit",
                data={
                    "name": "Updated Project",
                    "state": "Nevada",
                    "market": "Utilities",
                    "business_line": "Transmission",
                    "developer": "Updated Developer",
                    "general_contractor": "Updated GC",
                    "electrical_contractor": "Updated EC",
                    "status": "Completed",
                    "next_action": "Finalize report",
                },
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/project/1")
        save_projects.assert_called_once()


if __name__ == "__main__":
    unittest.main()
