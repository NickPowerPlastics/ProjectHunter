from pathlib import Path
from functools import wraps
import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import subprocess
from urllib.parse import quote, urlencode

from flask import Flask, abort, redirect, render_template, request, session, url_for

from discovery import DiscoveryEngine
from integrations.apollo import ApolloCompanyService
from intelligence_store import (
    IntelligenceValidationError,
    intelligence_store,
    parse_intelligence_json,
    preview_intelligence_payload,
)
from repositories.project_repository import calculate_score, load_projects, save_projects
from research import ResearchEngine
from research.intelligence import (
    build_actionable_opportunities,
    build_contractor_campaigns,
    build_project_research,
    get_contacts,
)
from dashboard_engine import build_activity, build_follow_ups, build_priorities, calculate_revenue

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency missing
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent


def load_environment() -> bool:
    if load_dotenv is None:
        return False

    dotenv_path = BASE_DIR / ".env"
    return bool(load_dotenv(dotenv_path=dotenv_path, override=False))


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
dismissed_follow_ups = set()
discovery_engine = DiscoveryEngine()
research_engine = ResearchEngine()

environment_loaded = load_environment()
apollo_service = ApolloCompanyService()
apollo_service.connection_status = "Not attempted"
apollo_service.last_connection_attempt = None
apollo_service.last_successful_connection = None

NAV_PAGES = {
    "dashboard": "home",
    "projects": "projects_page",
    "discover": "discover_projects_page",
    "companies": "companies_page",
    "accounts": "accounts_page",
    "contacts": "contacts_page",
    "tasks": "tasks_page",
}


def local_only(view):
    """Restrict sensitive administration to the machine running Project Hunter."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            is_loopback = ipaddress.ip_address(request.remote_addr or "").is_loopback
        except ValueError:
            is_loopback = False
        if not is_loopback:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def admin_csrf_token():
    token = session.get("admin_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["admin_csrf_token"] = token
    return token


def verify_admin_csrf():
    expected = session.get("admin_csrf_token", "")
    supplied = request.form.get("csrf_token", "")
    if not expected or not hmac.compare_digest(expected, supplied):
        abort(400, description="Invalid or missing form token.")


def read_submitted_feed():
    upload = request.files.get("json_file")
    if upload and upload.filename:
        try:
            return upload.read().decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise IntelligenceValidationError("The uploaded file must be UTF-8 JSON.") from error
    pasted = request.form.get("json_text", "").strip()
    if not pasted:
        raise IntelligenceValidationError("Upload a JSON file or paste JSON to continue.")
    return pasted


@app.after_request
def protect_admin_response(response):
    if request.endpoint == "intelligence_admin":
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'; form-action 'self'"
    return response


ACCOUNT_DATA = [
    {
        "id": 1,
        "name": "Rosendin",
        "company_type": "Electrical Contractor",
        "headquarters": "Dallas, TX",
        "website": "https://www.rosendin.com",
        "active_projects": 3,
        "opportunity_score": 92,
        "last_activity": "Follow-up sent 2 hours ago",
        "recommended_next_action": "Schedule a discovery call with the operations lead",
    },
    {
        "id": 2,
        "name": "Corbins",
        "company_type": "Developer",
        "headquarters": "Phoenix, AZ",
        "website": "https://www.corbins.com",
        "active_projects": 2,
        "opportunity_score": 87,
        "last_activity": "Meeting booked for next week",
        "recommended_next_action": "Send updated capability deck",
    },
    {
        "id": 3,
        "name": "Microsoft",
        "company_type": "Enterprise Customer",
        "headquarters": "Redmond, WA",
        "website": "https://www.microsoft.com",
        "active_projects": 5,
        "opportunity_score": 78,
        "last_activity": "Account review completed yesterday",
        "recommended_next_action": "Prepare a tailored expansion proposal",
    },
    {
        "id": 4,
        "name": "QTS",
        "company_type": "Data Center Operator",
        "headquarters": "Overland Park, KS",
        "website": "https://www.qtsdatacenters.com",
        "active_projects": 4,
        "opportunity_score": 84,
        "last_activity": "New project brief received",
        "recommended_next_action": "Validate fit against current portfolio",
    },
]


def build_companies(projects=None):
    if projects is None:
        return intelligence_store.companies()
    companies = []
    index = {}

    for project in projects:
        entries = [
            (project.get("developer") or "", "Developer"),
            (project.get("general_contractor") or "", "General Contractor"),
            (project.get("electrical_contractor") or "", "Electrical Contractor"),
            (project.get("civil_contractor") or "", "Civil Contractor"),
            (project.get("utility_company") or "", "Utility"),
            (project.get("supplier") or "", "Supplier"),
        ]

        for name, company_type in entries:
            if not name:
                continue
            key = (name.lower(), company_type)
            if key not in index:
                company_entry = {
                    "id": len(index) + 1,
                    "name": name,
                    "type": company_type,
                    "headquarters": "",
                    "website": "",
                    "states_worked": [],
                    "known_projects": [],
                    "total_opportunities": 0,
                    "total_quotes": 0,
                    "total_orders": 0,
                    "notes": "",
                    "projects": [],
                }
                index[key] = company_entry
                companies.append(company_entry)

            company_entry = index[key]
            company_entry["projects"].append(project)
            if project.get("state") and project.get("state") not in company_entry["states_worked"]:
                company_entry["states_worked"].append(project.get("state"))
            if project.get("name") and project.get("name") not in company_entry["known_projects"]:
                company_entry["known_projects"].append(project.get("name"))
            company_entry["total_opportunities"] += 1

    companies.sort(key=lambda company: company["name"].lower())
    return companies


def build_company_lookup(projects):
    lookup = {}
    for company in build_companies(projects):
        lookup[(company["name"].lower(), company["type"].lower())] = company["id"]
    return lookup


def load_discover_projects():
    return discovery_engine.load()


def serialize_discovery_projects(projects):
    return [
        {
            "project_name": project.project_name,
            "state": project.state,
            "market": project.market,
            "developer": project.developer,
            "estimated_stage": project.stage,
            "estimated_opportunity_score": project.opportunity_score,
            "imported": project.imported,
        }
        for project in projects
    ]


def build_opportunity_sections(projects):
    projects_needing_research = []
    ready_to_contact = []

    for project in projects:
        electrical_contractor = str(project.get("electrical_contractor") or "").strip()
        contacts = project.get("contacts") or []
        has_contacts = bool(contacts)

        if not electrical_contractor or not has_contacts:
            missing_parts = []
            if not electrical_contractor:
                missing_parts.append("Electrical Contractor")
            if not has_contacts:
                missing_parts.append("Contacts")
            projects_needing_research.append(
                {
                    "id": project.get("id"),
                    "name": project.get("name", "Untitled Project"),
                    "missing_information": ", ".join(missing_parts),
                }
            )
        elif electrical_contractor and has_contacts:
            ready_to_contact.append(
                {
                    "id": project.get("id"),
                    "name": project.get("name", "Untitled Project"),
                    "contractor": electrical_contractor,
                    "best_contact": contacts[0] if isinstance(contacts, list) else "Contact pending",
                    "recommended_next_action": project.get("next_action", "Follow up with the contractor"),
                }
            )

    return projects_needing_research, ready_to_contact


@app.route("/")
def home():
    intelligence = intelligence_store.snapshot()
    projects = intelligence["projects"]
    companies = intelligence_store.companies()
    company_ids = {company["name"].casefold(): company["id"] for company in companies}
    priorities = build_priorities(projects, intelligence["contacts"])
    for project in priorities:
        project["company_id"] = company_ids.get(project["company"].casefold())
    try:
        git_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BASE_DIR, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        git_commit = "unavailable"
    return render_template(
        "index.html",
        projects=projects,
        states=intelligence_store.states(),
        recent_discoveries=sorted(projects, key=lambda item: item.get("last_activity", ""), reverse=True)[:5],
        high_confidence=sorted(projects, key=lambda item: item.get("confidence", 0), reverse=True)[:5],
        needs_research=[item for item in projects if item.get("current_stage") == "Needs Research" or not item.get("electrical_contractor")][:5],
        recently_updated=sorted(projects, key=lambda item: item.get("last_activity", ""), reverse=True)[:5],
        metrics=intelligence_store.metrics(),
        priorities=priorities,
        activities=build_activity(projects, intelligence["contacts"]),
        follow_ups=build_follow_ups(projects, intelligence["contacts"], dismissed_follow_ups),
        revenue=calculate_revenue(projects),
        version=os.environ.get("PROJECT_HUNTER_VERSION", "1.0.0"),
        git_commit=git_commit,
        feed_date=intelligence.get("updated_at") or "Unavailable",
        freshness=intelligence_store.freshness(
            stale_after_days=int(os.environ.get("INTELLIGENCE_STALE_AFTER_DAYS", "3"))
        ),
        source=intelligence_store.source_label,
        last_updated=intelligence_store.last_updated,
        active_page="dashboard",
    )


@app.post("/follow-ups/<task_id>/dismiss")
def dismiss_follow_up(task_id):
    dismissed_follow_ups.add(task_id)
    if request.form.get("source") == "tasks":
        return redirect(url_for("tasks_page"))
    return redirect(url_for("home", _anchor="follow-ups"))


@app.post("/follow-ups/<task_id>/restore")
def restore_follow_up(task_id):
    dismissed_follow_ups.discard(task_id)
    return redirect(url_for("tasks_page"))


@app.route("/projects")
def projects_page():
    return render_template("projects.html", states=intelligence_store.states(), active_page="projects")


@app.route("/diagnostics", methods=["GET", "POST"])
def diagnostics_page():
    key_present = bool(apollo_service.api_key)
    diagnostics = None
    if request.method == "POST" and request.form.get("test_connection"):
        diagnostics = apollo_service.test_connection()

    return render_template(
        "diagnostics.html",
        key_present=key_present,
        key_length=len(apollo_service.api_key or ""),
        environment_loaded=environment_loaded,
        last_attempt=apollo_service.last_connection_attempt or "Not attempted",
        connection_status=apollo_service.connection_status,
        last_successful_connection=apollo_service.last_successful_connection or "Not available",
        diagnostics=diagnostics,
        active_page="dashboard",
    )


@app.route("/companies")
def companies_page():
    companies = intelligence_store.companies()
    return render_template("companies.html", companies=companies, active_page="companies")


@app.route("/accounts")
def accounts_page():
    return render_template("accounts.html", accounts=ACCOUNT_DATA, active_page="accounts")


@app.route("/account/<int:account_id>")
def account_workspace(account_id):
    account = next((item for item in ACCOUNT_DATA if item.get("id") == account_id), None)
    if account is None:
        return "Account not found", 404

    return render_template("account_workspace.html", account=account, active_page="accounts")


@app.route("/company/<int:company_id>", methods=["GET", "POST"])
def company_details(company_id):
    companies = intelligence_store.companies()
    company = next((item for item in companies if item.get("id") == company_id), None)

    if company is None:
        return "Company not found", 404

    apollo_profile = None
    if request.method == "POST":
        apollo_profile = apollo_service.lookup_company(company.get("name", ""))
        company["apollo_profile"] = {
            "company_name": apollo_profile.company_name,
            "website": apollo_profile.website,
            "headquarters": apollo_profile.headquarters,
            "employee_count": apollo_profile.employee_count,
            "industry": apollo_profile.industry,
            "revenue_range": apollo_profile.revenue_range,
            "number_of_contacts": apollo_profile.number_of_contacts,
            "last_updated": apollo_profile.last_updated,
        }

    return render_template(
        "company.html",
        company=company,
        apollo_profile=company.get("apollo_profile"),
        active_page="companies",
    )


@app.get("/search")
def global_search():
    query = request.args.get("q", "").strip()
    needle = query.casefold()
    data = intelligence_store.snapshot()
    companies = intelligence_store.companies()
    states = intelligence_store.states()
    contains = lambda value: needle and needle in str(value or "").casefold()
    results = {
        "projects": [p for p in data["projects"] if any(contains(p.get(field)) for field in ("name", "state", "developer", "general_contractor", "electrical_contractor", "mechanical_contractor"))],
        "companies": [c for c in companies if contains(c["name"]) or contains(c["type"])],
        "contacts": [c for c in data["contacts"] if any(contains(c.get(field)) for field in ("name", "company", "title", "email", "location"))],
        "states": [s for s in states if contains(s["name"])],
    }
    return render_template("search.html", query=query, results=results, active_page="search")


def prepare_actionable_opportunities(region):
    opportunities = [item for item in build_actionable_opportunities() if not region or any(
        project.get("key") == item.get("key") and project.get("state") == region
        for project in intelligence_store.snapshot()["projects"]
    )]
    for opportunity in opportunities:
        for contact in opportunity.get("contacts", []):
            contact["email_url"] = build_contact_email_url(contact)
        best_contact = opportunity.get("best_contact")
        if best_contact:
            best_contact["email_url"] = build_contact_email_url(best_contact)
    return opportunities


@app.route("/discover")
def discover_projects_page():
    region = request.args.get("region", "Arizona")
    market = request.args.get("market", "Data Centers")
    discover_projects = serialize_discovery_projects(
        [
            project for project in load_discover_projects()
            if (not region or project.state == region) and (not market or project.market == market)
        ]
    )

    projects = load_projects()
    projects_needing_research, ready_to_contact = build_opportunity_sections(projects)
    actionable_opportunities = prepare_actionable_opportunities(region)
    contractor_campaigns = build_contractor_campaigns() if region == "Arizona" else []

    return render_template(
        "discover_projects.html",
        discover_projects=discover_projects,
        projects_needing_research=projects_needing_research,
        ready_to_contact=ready_to_contact,
        actionable_opportunities=actionable_opportunities,
        contractor_campaigns=contractor_campaigns,
        region=region,
        market=market,
        active_page="discover",
    )


@app.route("/discover/run", methods=["POST"])
def run_discovery():
    region = request.form.get("region", "Arizona")
    market = request.form.get("market", "Data Centers")
    discovery_engine.run(region=region, market=market)
    projects = load_projects()
    projects_needing_research, ready_to_contact = build_opportunity_sections(projects)
    actionable_opportunities = prepare_actionable_opportunities(region)
    contractor_campaigns = build_contractor_campaigns() if region == "Arizona" else []

    return render_template(
        "discover_projects.html",
        discover_projects=serialize_discovery_projects(
            [
                project for project in load_discover_projects()
                if (not region or project.state == region) and (not market or project.market == market)
            ]
        ),
        projects_needing_research=projects_needing_research,
        ready_to_contact=ready_to_contact,
        actionable_opportunities=actionable_opportunities,
        contractor_campaigns=contractor_campaigns,
        region=region,
        market=market,
        message="Discovery run complete.",
        active_page="discover",
    )


@app.route("/discover/import", methods=["POST"])
def import_discovered_project():
    project_name = request.form.get("project_name", "")
    region = request.form.get("region", "")
    market = request.form.get("market", "")
    projects = load_projects()

    existing_match = next((project for project in projects if str(project.get("name", "")).lower() == str(project_name).lower()), None)
    if existing_match is not None:
        projects_needing_research, ready_to_contact = build_opportunity_sections(projects)
        return render_template(
            "discover_projects.html",
            discover_projects=serialize_discovery_projects(
                [
                    project for project in load_discover_projects()
                    if (not region or project.state == region) and (not market or project.market == market)
                ]
            ),
            projects_needing_research=projects_needing_research,
            ready_to_contact=ready_to_contact,
            region=region,
            market=market,
            message=f"{project_name} is already imported.",
            active_page="discover",
        )

    discover_projects = load_discover_projects()
    project_data = next((project for project in discover_projects if project.project_name.lower() == str(project_name).lower()), None)
    if project_data is None:
        projects_needing_research, ready_to_contact = build_opportunity_sections(projects)
        return render_template(
            "discover_projects.html",
            discover_projects=serialize_discovery_projects(
                [
                    project for project in load_discover_projects()
                    if (not region or project.state == region) and (not market or project.market == market)
                ]
            ),
            projects_needing_research=projects_needing_research,
            ready_to_contact=ready_to_contact,
            region=region,
            market=market,
            message="Unable to find that project in the discovery list.",
            active_page="discover",
        )

    new_project = {
        "id": max((project.get("id", 0) for project in projects), default=0) + 1,
        "name": project_data.project_name,
        "state": project_data.state,
        "market": project_data.market,
        "business_line": project_data.business_line or "Duct Bank",
        "developer": project_data.developer,
        "general_contractor": "",
        "electrical_contractor": "",
        "contacts": [],
        "status": "New",
        "next_action": "Follow up with developer",
    }
    new_project["score"] = calculate_score(new_project)
    projects.append(new_project)
    save_projects(projects)
    discovery_engine.mark_imported(project_name)

    projects_needing_research, ready_to_contact = build_opportunity_sections(projects)
    return render_template(
        "discover_projects.html",
        discover_projects=serialize_discovery_projects(
            [
                project for project in load_discover_projects()
                if (not region or project.state == region) and (not market or project.market == market)
            ]
        ),
        projects_needing_research=projects_needing_research,
        ready_to_contact=ready_to_contact,
        region=region,
        market=market,
        message=f"{project_name} imported successfully.",
        active_page="discover",
    )


def build_contact_email_url(contact):
    email = str(contact.get("email", "")).strip()
    name = str(contact.get("name", "")).strip()
    first_name = str(contact.get("first_name", "")).strip() or (name.split()[0] if name else "there")

    subject = "Arizona data center duct bank support - Proven Supplier"
    body = f"""Hi {first_name},

My name is Nick, and I work with Power Plastics. We manufacture custom machined plastic components used on large infrastructure projects, including conduit spacers, cable management components, wear parts, and other engineered plastic products.

I've been following the growth of data center construction in Arizona and noticed {contact.get('company', 'your company')} continues to be involved in many mission-critical projects. I wanted to introduce myself and see who on your team handles sourcing or evaluating products like conduit spacers and other custom plastic components.

If there is someone else I should be speaking with, I'd appreciate being pointed in the right direction.

Thanks,"""

    query = urlencode({
        "bcc": "20887200@bcc.na2.hubspot.com",
        "subject": subject,
        "body": body,
    }, quote_via=quote)
    return f"mailto:{quote(email, safe='@')}?{query}"


@app.route("/contacts")
def contacts_page():
    company = request.args.get("company", "").strip()
    intelligence = intelligence_store.snapshot()
    contacts = [contact for contact in intelligence["contacts"] if not company or contact.get("company") == company]
    for contact in contacts:
        contact["email_url"] = build_contact_email_url(contact) if contact["ready_to_email"] else None
    companies = sorted({contact.get("company", "") for contact in intelligence["contacts"] if contact.get("company")})
    return render_template(
        "contacts.html",
        contacts=contacts,
        companies=companies,
        selected_company=company,
        source=intelligence_store.source_label,
        last_updated=intelligence_store.last_updated,
        active_page="contacts",
    )


@app.route("/contact/<int:contact_id>")
def contact_details(contact_id):
    contacts = intelligence_store.snapshot()["contacts"]
    contact = next((item for item in contacts if item.get("id") == contact_id), None)
    if contact is None:
        return "Contact not found", 404
    contact["email_url"] = build_contact_email_url(contact) if contact["ready_to_email"] else None
    return render_template("contact.html", contact=contact, active_page="contacts")


@app.post("/intelligence/sync")
def sync_intelligence():
    intelligence_store.reload()
    return redirect(request.form.get("next") or url_for("home"))


@app.route("/admin/intelligence", methods=["GET", "POST"])
@local_only
def intelligence_admin():
    message = session.pop("intelligence_admin_message", None)
    error = None
    preview = None
    json_text = ""
    status = 200

    if request.method == "POST":
        verify_admin_csrf()
        try:
            json_text = read_submitted_feed()
            payload = parse_intelligence_json(json_text)
            preview = preview_intelligence_payload(payload)
            json_text = json.dumps(payload, indent=2, ensure_ascii=False)
            payload_digest = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest()
            if request.form.get("action") == "import":
                expected_digest = session.get("intelligence_preview_digest", "")
                if (
                    request.form.get("preview_confirmed") != "1"
                    or not expected_digest
                    or not hmac.compare_digest(expected_digest, payload_digest)
                ):
                    raise IntelligenceValidationError("Preview and confirm the feed before importing it.")
                backup_path = intelligence_store.replace(payload)
                session.pop("intelligence_preview_digest", None)
                backup_label = f"data/backups/{backup_path.name}" if backup_path else "No prior feed existed"
                session["intelligence_admin_message"] = (
                    f"Imported {preview['project_count']} projects and {preview['contact_count']} contacts. "
                    f"Backup: {backup_label}."
                )
                return redirect(url_for("intelligence_admin"))
            session["intelligence_preview_digest"] = payload_digest
        except IntelligenceValidationError as validation_error:
            error = str(validation_error)
            status = 400

    with intelligence_store.path.open(encoding="utf-8") as handle:
        current_preview = preview_intelligence_payload(json.load(handle))
    return render_template(
        "intelligence_admin.html",
        current_preview=current_preview,
        preview=preview,
        json_text=json_text,
        error=error,
        message=message,
        csrf_token=admin_csrf_token(),
        active_page="admin",
    ), status


@app.route("/tasks")
def tasks_page():
    intelligence = intelligence_store.snapshot()
    all_tasks = build_follow_ups(intelligence["projects"], intelligence["contacts"])
    active_tasks = [task for task in all_tasks if task["id"] not in dismissed_follow_ups]
    dismissed_tasks = [task for task in all_tasks if task["id"] in dismissed_follow_ups]
    selected_type = request.args.get("type", "").strip()
    selected_state = request.args.get("state", "").strip()
    filtered_tasks = [
        task for task in active_tasks
        if (not selected_type or task["kind"] == selected_type)
        and (not selected_state or task["project"].get("state") == selected_state)
    ]
    reason_options = sorted({(task["kind"], task["reason"]) for task in all_tasks}, key=lambda item: item[1])
    state_options = sorted({task["project"].get("state") or "Unassigned" for task in all_tasks})
    return render_template(
        "tasks.html",
        tasks=filtered_tasks,
        dismissed_tasks=dismissed_tasks,
        selected_type=selected_type,
        selected_state=selected_state,
        reason_options=reason_options,
        state_options=state_options,
        counts={
            "due": len(active_tasks),
            "research": sum(task["kind"] == "research-incomplete" for task in active_tasks),
            "contacts": sum(task["kind"] == "contractor-no-contacts" for task in active_tasks),
            "high_priority": sum(task["priority_score"] >= 70 for task in active_tasks),
        },
        active_page="tasks",
    )


@app.route("/project/<int:project_id>/favorite", methods=["POST"])
def toggle_favorite(project_id):
    projects = load_projects()
    project = next((item for item in projects if item.get("id") == project_id), None)

    if project is None:
        return "Project not found", 404

    project["favorite"] = not bool(project.get("favorite", False))
    save_projects(projects)
    return redirect(url_for("home"))


@app.route("/project/<int:project_id>")
def project_details(project_id):
    projects = intelligence_store.snapshot()["projects"]
    project = next((item for item in projects if item.get("id") == project_id), None)

    if project is None:
        return "Project not found", 404

    company_lookup = {(company["name"].lower(), company_type.lower()): company["id"]
                      for company in intelligence_store.companies() for company_type in company["types"]}
    contractor_candidates = project.get("contractor_candidates") or []
    apollo_setup_message = project.get("apollo_setup_message")
    return render_template(
        "project.html",
        project=project,
        company_lookup=company_lookup,
        contractor_candidates=contractor_candidates,
        apollo_setup_message=apollo_setup_message,
        active_page="dashboard",
    )


def build_research_workspace(project, research_results):
    def pick(section, fallback):
        for result in research_results:
            if result.get("section") == section and result.get("content"):
                return result.get("content")
        return fallback

    score = project.get("score") or 0
    score_label = f"{score}/100"
    research_status = project.get("status") or "Needs Review"
    next_action = project.get("next_action") or "Schedule follow-up"

    return {
        "workspace_tabs": ["Overview", "Contractors", "Contacts", "News", "Documents", "AI Notes", "Timeline"],
        "summary_cards": [
            {"title": "Opportunity Score", "value": score_label},
            {"title": "Research Status", "value": research_status},
            {"title": "Next Action", "value": next_action},
        ],
        "overview_content": pick("Project Overview", "No research available yet."),
        "developer_content": pick("Developer", "No research available yet."),
        "general_contractor_content": pick("General Contractor", "No research available yet."),
        "electrical_contractor_content": pick("Electrical Contractor", "No research available yet."),
        "civil_contractor_content": pick("Civil Contractor", "No research available yet."),
        "utility_content": pick("Utility Company", "No research available yet."),
        "news_content": pick("Project News", "No research available yet."),
        "documents_content": pick("Permit Information", "No documents captured yet."),
        "contacts_content": pick("Apollo Contacts", "No contact research available yet."),
        "ai_notes_content": pick("AI Notes", "No research available yet."),
        "timeline_content": pick("Recommended Next Action", "No timeline entries yet."),
        "research_hint": "Research providers coming soon." if not research_results else "Live research results are ready for review.",
    }


@app.route("/project/<int:project_id>/research", methods=["GET", "POST"])
def project_research(project_id):
    projects = load_projects()
    project = next((item for item in projects if item.get("id") == project_id), None)

    if project is None:
        return "Project not found", 404

    research_results = []
    if request.method == "POST":
        research_results = research_engine.run(project)

    intelligence = build_project_research(project)
    workspace = build_research_workspace(project, research_results)
    if intelligence.get("record"):
        record = intelligence["record"]
        workspace["developer_content"] = record.get("developer") or workspace["developer_content"]
        workspace["general_contractor_content"] = record.get("general_contractor") or workspace["general_contractor_content"]
        workspace["timeline_content"] = intelligence.get("next_action") or workspace["timeline_content"]
        workspace["research_hint"] = "Actionable contractor intelligence loaded from the Arizona intelligence pack."

    return render_template(
        "research.html",
        project=project,
        research_results=research_results,
        workspace=workspace,
        intelligence=intelligence,
        active_page="dashboard",
    )


@app.route("/project/<int:project_id>/find-electrical-contractor", methods=["POST"])
def find_electrical_contractor(project_id):
    projects = load_projects()
    project = next((item for item in projects if item.get("id") == project_id), None)

    if project is None:
        return "Project not found", 404

    contractor_name = (project.get("electrical_contractor") or "").strip()
    state = (project.get("state") or "").strip()
    project_message = None

    try:
        contacts = apollo_service.search_contacts(contractor_name or project.get("name", ""), state)
        top_contacts = contacts[:5]
        project["apollo_contacts"] = [
            {
                "name": contact.name,
                "title": contact.title,
                "company": contact.company,
                "location": contact.location,
                "email_status": contact.email_status,
                "person_id": contact.person_id,
                "linkedin_url": contact.linkedin_url,
                "business_email": contact.business_email,
                "retrieval_date": contact.retrieval_date,
            }
            for contact in top_contacts
        ]
        project["contacts"] = [contact["name"] for contact in project["apollo_contacts"]]
        project["contractor_candidates"] = [
            {
                "candidate_name": contact["name"],
                "confidence_score": 95,
                "source_url": contact["linkedin_url"],
                "evidence_snippet": f"{contact['title']} • {contact['location']} • {contact['email_status']} • {contact.get('business_email') or 'email unavailable'}",
            }
            for contact in project["apollo_contacts"]
        ]
    except RuntimeError as exc:
        project_message = str(exc)
        project["apollo_contacts"] = []
        project["contacts"] = []
        project["contractor_candidates"] = []

    save_projects(projects)
    project["apollo_setup_message"] = project_message
    return redirect(url_for("project_details", project_id=project_id))


@app.route("/project/<int:project_id>/confirm-contractor", methods=["POST"])
def confirm_contractor(project_id):
    projects = load_projects()
    project = next((item for item in projects if item.get("id") == project_id), None)

    if project is None:
        return "Project not found", 404

    candidate_name = request.form.get("candidate_name", "").strip()
    candidate_company = request.form.get("candidate_company", "").strip()
    if candidate_name:
        project["electrical_contractor"] = candidate_company or candidate_name
        project["contractor_candidates"] = []
        save_projects(projects)
    return redirect(url_for("project_details", project_id=project_id))


@app.route("/project/add", methods=["GET", "POST"])
def add_project():
    if request.method == "POST":
        projects = load_projects()
        next_id = max((project.get("id", 0) for project in projects), default=0) + 1
        new_project = {
            "id": next_id,
            "name": request.form.get("name", ""),
            "state": request.form.get("state", ""),
            "market": request.form.get("market", ""),
            "business_line": request.form.get("business_line", ""),
            "developer": request.form.get("developer", ""),
            "general_contractor": request.form.get("general_contractor", ""),
            "electrical_contractor": request.form.get("electrical_contractor", ""),
            "status": request.form.get("status", ""),
            "next_action": request.form.get("next_action", ""),
        }
        new_project["score"] = calculate_score(new_project)
        projects.append(new_project)
        save_projects(projects)
        return redirect(url_for("home"))

    return render_template("add_project.html", active_page="dashboard")


@app.route("/project/<int:project_id>/edit", methods=["GET", "POST"])
def edit_project(project_id):
    projects = load_projects()
    project = next((item for item in projects if item.get("id") == project_id), None)

    if project is None:
        return "Project not found", 404

    if request.method == "POST":
        project.update(
            {
                "name": request.form.get("name", project.get("name", "")),
                "state": request.form.get("state", project.get("state", "")),
                "market": request.form.get("market", project.get("market", "")),
                "business_line": request.form.get("business_line", project.get("business_line", "")),
                "developer": request.form.get("developer", project.get("developer", "")),
                "general_contractor": request.form.get("general_contractor", project.get("general_contractor", "")),
                "electrical_contractor": request.form.get("electrical_contractor", project.get("electrical_contractor", "")),
                "status": request.form.get("status", project.get("status", "")),
                "next_action": request.form.get("next_action", project.get("next_action", "")),
            }
        )
        project["score"] = calculate_score(project)
        save_projects(projects)
        return redirect(url_for("project_details", project_id=project_id))

    return render_template("edit_project.html", project=project, active_page="dashboard")


if __name__ == "__main__":
    app.run(debug=True)
