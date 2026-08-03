import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import app as app_module
from app import app
from integrations.apollo import ApolloCompanyService, ApolloContact


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
        self.assertIn(b"Run Provider Research", response.data)
        self.assertIn(b"No saved intelligence match", response.data)

    def test_research_workspace_renders_tabs_and_summary(self):
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
                "civil_contractor": "Example Civil",
                "utility_company": "Example Utility",
                "status": "In Progress",
                "next_action": "Schedule site visit",
            }
        ]

        with patch("app.load_projects", return_value=projects):
            response = self.client.get("/project/1/research")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Research Workspace", response.data)
        self.assertIn(b"Overview", response.data)
        self.assertIn(b"Contractors", response.data)
        self.assertIn(b"Contacts", response.data)
        self.assertIn(b"News", response.data)
        self.assertIn(b"Documents", response.data)
        self.assertIn(b"AI Notes", response.data)
        self.assertIn(b"Timeline", response.data)
        self.assertIn(b"Opportunity Score", response.data)
        self.assertIn(b"Research Status", response.data)

    def test_research_run_uses_engine_and_displays_provider_result(self):
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
            response = self.client.post(
                "/project/1/research",
                data={},
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Contractor Intelligence", response.data)
        self.assertIn(b"Initial outreach", response.data)

    def test_dashboard_renders_sidebar_navigation(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/projects", response.data)
        self.assertIn(b"/companies", response.data)
        self.assertIn(b"/contacts", response.data)
        self.assertIn(b"/tasks", response.data)
        self.assertIn(b'nav-link active', response.data)

    def test_diagnostics_page_renders_apollo_status(self):
        with patch.object(app_module.apollo_service, "api_key", "secret-key"), patch.object(app_module.apollo_service, "connection_status", "Not attempted"), patch.object(app_module, "environment_loaded", True):
            response = self.client.get("/diagnostics")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Apollo API key detected: Yes", response.data)
        self.assertIn(b"Key length:", response.data)
        self.assertIn(b"Environment loaded: Yes", response.data)
        self.assertIn(b"Last Apollo connection attempt", response.data)
        self.assertIn(b"Connection status", response.data)

    def test_diagnostics_page_renders_connection_test_results(self):
        with patch.object(app_module.apollo_service, "test_connection", return_value={
            "connected": True,
            "company_accessible": True,
            "response_time_ms": 142,
            "rate_limit": "100 remaining",
            "error_message": None,
            "error_status_code": None,
        }):
            response = self.client.post("/diagnostics", data={"test_connection": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Connected: Yes", response.data)
        self.assertIn(b"Company/account accessible: Yes", response.data)
        self.assertIn(b"API response time", response.data)
        self.assertIn(b"100 remaining", response.data)

    def test_diagnostics_page_renders_apollo_connection_section(self):
        with patch.object(app_module.apollo_service, "api_key", "secret-key"), patch.object(app_module.apollo_service, "connection_status", "Not attempted"), patch.object(app_module.apollo_service, "last_successful_connection", None), patch.object(app_module, "environment_loaded", True):
            response = self.client.get("/diagnostics")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Apollo Connection", response.data)
        self.assertIn(b"Authentication Status", response.data)
        self.assertIn(b"Last Successful Connection", response.data)

    def test_load_environment_uses_project_root_dotenv(self):
        with patch.object(app_module, "load_dotenv", return_value=True) as load_dotenv_mock:
            loaded = app_module.load_environment()

        self.assertTrue(loaded)
        load_dotenv_mock.assert_called_once_with(dotenv_path=app_module.BASE_DIR / ".env", override=False)

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

    def test_accounts_navigation_and_workspace_render(self):
        response = self.client.get("/accounts")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Accounts", response.data)
        self.assertIn(b"Rosendin", response.data)
        self.assertIn(b"Microsoft", response.data)

        response = self.client.get("/account/1")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Overview", response.data)
        self.assertIn(b"Projects", response.data)
        self.assertIn(b"Contacts", response.data)
        self.assertIn(b"HubSpot", response.data)
        self.assertIn(b"Apollo", response.data)
        self.assertIn(b"Method", response.data)
        self.assertIn(b"Notes", response.data)
        self.assertIn(b"Activity", response.data)
        self.assertIn(b"Company Name", response.data)
        self.assertIn(b"Active Projects", response.data)
        self.assertIn(b"Opportunity Score", response.data)
        self.assertIn(b"Recommended Next Action", response.data)

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
        self.assertIn(b"Headquarters", response.data)
        self.assertIn(b"Website", response.data)
        self.assertIn(b"States Worked", response.data)
        self.assertIn(b"Known Projects", response.data)
        self.assertIn(b"Total Opportunities", response.data)
        self.assertIn(b"Total Quotes", response.data)
        self.assertIn(b"Total Orders", response.data)
        self.assertIn(b"Notes", response.data)

    def test_project_details_page_links_companies(self):
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
            }
        ]

        with patch("app.load_projects", return_value=projects):
            response = self.client.get("/project/1")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/company/1", response.data)
        self.assertIn(b"/company/2", response.data)
        self.assertIn(b"/company/3", response.data)

    def test_project_details_page_renders_find_contractor_button(self):
        projects = [
            {
                "id": 1,
                "name": "Project One",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "Example GC",
                "electrical_contractor": "",
                "status": "In Progress",
                "next_action": "Continue",
            }
        ]

        with patch("app.load_projects", return_value=projects):
            response = self.client.get("/project/1")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Find Electrical Contractor", response.data)

    def test_apollo_contact_search_ranks_titles_and_caps_results(self):
        service = ApolloCompanyService(api_key="test-key")
        payload = {
            "contacts": [
                {
                    "name": "Low Priority",
                    "title": "Project Manager",
                    "company_name": "North Star Electric",
                    "city": "Phoenix",
                    "state": "AZ",
                    "email": "low@example.com",
                    "email_status": "verified",
                    "linkedin_url": "https://linkedin.com/in/low",
                    "id": "person-001",
                },
                {
                    "name": "Top Priority",
                    "title": "Chief Estimator",
                    "company_name": "North Star Electric",
                    "city": "Denver",
                    "state": "CO",
                    "email": "top@example.com",
                    "email_status": "verified",
                    "linkedin_url": "https://linkedin.com/in/top",
                    "id": "person-002",
                },
                {
                    "name": "Second Priority",
                    "title": "Senior Estimator",
                    "company_name": "North Star Electric",
                    "city": "Las Vegas",
                    "state": "NV",
                    "email": None,
                    "email_status": "unverified",
                    "linkedin_url": "https://linkedin.com/in/second",
                    "id": "person-003",
                },
                {
                    "name": "Third Priority",
                    "title": "Purchasing Manager",
                    "company_name": "North Star Electric",
                    "city": "Austin",
                    "state": "TX",
                    "email": None,
                    "email_status": "unverified",
                    "linkedin_url": "https://linkedin.com/in/third",
                    "id": "person-004",
                },
                {
                    "name": "Fourth Priority",
                    "title": "Project Executive",
                    "company_name": "North Star Electric",
                    "city": "Salt Lake City",
                    "state": "UT",
                    "email": None,
                    "email_status": "unverified",
                    "linkedin_url": "https://linkedin.com/in/fourth",
                    "id": "person-005",
                },
                {
                    "name": "Fifth Priority",
                    "title": "Electrical Project Manager",
                    "company_name": "North Star Electric",
                    "city": "Boise",
                    "state": "ID",
                    "email": None,
                    "email_status": "unverified",
                    "linkedin_url": "https://linkedin.com/in/fifth",
                    "id": "person-006",
                },
            ]
        }

        with patch.object(service, "_request_json", return_value=payload):
            contacts = service.search_contacts("North Star Electric", "Arizona")

        self.assertEqual(len(contacts), 5)
        self.assertEqual(contacts[0].title, "Chief Estimator")
        self.assertEqual(contacts[0].email_status, "verified")
        self.assertEqual(contacts[1].title, "Senior Estimator")
        self.assertEqual(contacts[2].title, "Purchasing Manager")
        self.assertEqual(contacts[3].title, "Project Executive")
        self.assertEqual(contacts[4].title, "Electrical Project Manager")

    def test_find_electrical_contractor_displays_candidates_and_confirm_flow(self):
        projects = [
            {
                "id": 1,
                "name": "Project One",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "Example GC",
                "electrical_contractor": "North Star Electric",
                "state": "Arizona",
                "status": "In Progress",
                "next_action": "Continue",
            }
        ]

        candidates = [
            ApolloContact(
                name="Jordan Mills",
                title="Preconstruction Manager",
                company="North Star Electric",
                location="Phoenix, AZ",
                email_status="verified",
                person_id="person-001",
                linkedin_url="https://linkedin.com/in/jordanmills",
            ),
            ApolloContact(
                name="Taylor Brooks",
                title="Senior Estimator",
                company="North Star Electric",
                location="Las Vegas, NV",
                email_status="available",
                person_id="person-002",
                linkedin_url="https://linkedin.com/in/taylorbrooks",
            ),
        ]

        with patch("app.load_projects", return_value=projects), patch("app.save_projects") as save_projects, patch("app.apollo_service.search_contacts", return_value=candidates):
            response = self.client.post("/project/1/find-electrical-contractor", data={}, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Jordan Mills", response.data)
        self.assertIn(b"Preconstruction Manager", response.data)
        self.assertIn(b"Confirm Contractor", response.data)
        self.assertEqual(projects[0]["contacts"], ["Jordan Mills", "Taylor Brooks"])
        self.assertEqual(projects[0]["apollo_contacts"][0]["name"], "Jordan Mills")

        with patch("app.load_projects", return_value=projects), patch("app.save_projects") as save_projects:
            response = self.client.post(
                "/project/1/confirm-contractor",
                data={"candidate_name": "Jordan Mills", "candidate_company": "North Star Electric"},
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/project/1")
        self.assertEqual(projects[0]["electrical_contractor"], "North Star Electric")
        save_projects.assert_called_once()

    def test_find_electrical_contractor_shows_clear_message_when_apollo_not_configured(self):
        projects = [
            {
                "id": 1,
                "name": "Project One",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "Example GC",
                "electrical_contractor": "North Star Electric",
                "state": "Arizona",
                "status": "In Progress",
                "next_action": "Continue",
            }
        ]

        with patch("app.load_projects", return_value=projects), patch("app.save_projects") as save_projects, patch("app.apollo_service.search_contacts", side_effect=RuntimeError("missing api key")):
            response = self.client.post("/project/1/find-electrical-contractor", data={}, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"APOLLO_API_KEY", response.data)
        self.assertIn(b"setup", response.data.lower())
        save_projects.assert_called_once()

    def test_discover_projects_page_renders_search_form_and_results(self):
        response = self.client.get("/discover?region=Arizona&market=Data%20Centers")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Discover Projects", response.data)
        self.assertIn(b"Search Region", response.data)
        self.assertIn(b"Data Centers", response.data)
        self.assertIn(b"West Valley", response.data)
        self.assertIn(b"Import", response.data)

    def test_opportunity_finder_renders_new_sections(self):
        projects = [
            {
                "id": 1,
                "name": "Imported Project",
                "state": "Arizona",
                "market": "Data Centers",
                "business_line": "Duct Bank",
                "developer": "Example Developer",
                "general_contractor": "",
                "electrical_contractor": "",
                "status": "Needs Research",
                "next_action": "Research",
                "contacts": [],
            }
        ]
        discovered = [
            SimpleNamespace(
                project_name="Fresh Opportunity",
                state="Arizona",
                market="Data Centers",
                developer="Example Developer",
                stage="Early Planning",
                opportunity_score=88,
                imported=False,
                business_line="Duct Bank",
            )
        ]

        with patch("app.load_projects", return_value=projects), patch("app.load_discover_projects", return_value=discovered):
            response = self.client.get("/discover?region=Arizona&market=Data%20Centers")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Opportunity Finder", response.data)
        self.assertIn(b"New Opportunities", response.data)
        self.assertIn(b"Projects Needing Research", response.data)
        self.assertIn(b"Ready to Contact", response.data)
        self.assertIn(b"Fresh Opportunity", response.data)
        self.assertIn(b"Imported Project", response.data)

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


    def test_contacts_page_renders_actionable_contacts(self):
        response = self.client.get("/contacts")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Arizona Outreach Contacts", response.data)
        self.assertIn(b"Charlie Johnson", response.data)
        self.assertIn(b"c.johnson@corbins.us", response.data)
        self.assertIn(b"mailto:", response.data)

    def test_microsoft_goodyear_research_loads_saved_intelligence(self):
        projects = [{
            "id": 1,
            "name": "Microsoft Goodyear",
            "state": "Arizona",
            "market": "Data Centers",
            "business_line": "Duct Bank",
            "developer": "Microsoft",
            "general_contractor": "",
            "electrical_contractor": "",
            "status": "Research needed",
            "next_action": "Identify electrical contractor",
            "score": 60,
        }]
        with patch("app.load_projects", return_value=projects):
            response = self.client.get("/project/1/research")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Specified Electrical Contractors", response.data)
        self.assertIn(b"55%", response.data)
        self.assertIn(b"PHX71 BIM project reference", response.data)

    def test_contacts_email_link_is_personalized(self):
        response = self.client.get("/contacts?company=Corbins")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Arizona%20data%20center%20duct%20bank%20support%20-%20Proven%20Supplier", response.data)
        self.assertIn(b"Hi%20Charlie%2C", response.data)
        self.assertIn(b"noticed%20Corbins%20continues", response.data)
        self.assertIn(b"bcc=20887200%40bcc.na2.hubspot.com", response.data)


if __name__ == "__main__":
    unittest.main()
