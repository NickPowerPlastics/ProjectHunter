from flask import Flask, redirect, render_template, request, url_for

from discovery import DiscoveryEngine
from repositories.project_repository import calculate_score, load_projects, save_projects

app = Flask(__name__)
discovery_engine = DiscoveryEngine()

NAV_PAGES = {
    "dashboard": "home",
    "projects": "projects_page",
    "discover": "discover_projects_page",
    "companies": "companies_page",
    "contacts": "contacts_page",
    "tasks": "tasks_page",
}


def build_companies(projects):
    companies = []
    index = {}

    for project in projects:
        entries = [
            (project.get("developer") or "", "Developer"),
            (project.get("general_contractor") or "", "General Contractor"),
            (project.get("electrical_contractor") or "", "Electrical Contractor"),
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
                    "projects": [],
                }
                index[key] = company_entry
                companies.append(company_entry)
            index[key]["projects"].append(project)

    companies.sort(key=lambda company: company["name"].lower())
    return companies


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


@app.route("/")
def home():
    projects = load_projects()
    favorites = [project for project in projects if project.get("favorite", False)]
    non_favorites = [project for project in projects if not project.get("favorite", False)]
    favorites = sorted(favorites, key=lambda project: project.get("score", 0), reverse=True)
    non_favorites = sorted(non_favorites, key=lambda project: project.get("score", 0), reverse=True)
    ordered_projects = favorites + non_favorites
    has_favorites = any(project.get("favorite", False) for project in ordered_projects)
    return render_template("index.html", projects=ordered_projects, has_favorites=has_favorites, active_page="dashboard")


@app.route("/projects")
def projects_page():
    return render_template("page.html", title="Projects", content="Projects page coming soon.", active_page="projects")


@app.route("/companies")
def companies_page():
    companies = build_companies(load_projects())
    return render_template("companies.html", companies=companies, active_page="companies")


@app.route("/company/<int:company_id>")
def company_details(company_id):
    companies = build_companies(load_projects())
    company = next((item for item in companies if item.get("id") == company_id), None)

    if company is None:
        return "Company not found", 404

    return render_template("company.html", company=company, active_page="companies")


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
    return render_template(
        "discover_projects.html",
        discover_projects=discover_projects,
        region=region,
        market=market,
        active_page="discover",
    )


@app.route("/discover/run", methods=["POST"])
def run_discovery():
    region = request.form.get("region", "Arizona")
    market = request.form.get("market", "Data Centers")
    discovery_engine.run(region=region, market=market)
    return render_template(
        "discover_projects.html",
        discover_projects=serialize_discovery_projects(
            [
                project for project in load_discover_projects()
                if (not region or project.state == region) and (not market or project.market == market)
            ]
        ),
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
        return render_template(
            "discover_projects.html",
            discover_projects=serialize_discovery_projects(
                [
                    project for project in load_discover_projects()
                    if (not region or project.state == region) and (not market or project.market == market)
                ]
            ),
            region=region,
            market=market,
            message=f"{project_name} is already imported.",
            active_page="discover",
        )

    discover_projects = load_discover_projects()
    project_data = next((project for project in discover_projects if project.project_name.lower() == str(project_name).lower()), None)
    if project_data is None:
        return render_template(
            "discover_projects.html",
            discover_projects=serialize_discovery_projects(
                [
                    project for project in load_discover_projects()
                    if (not region or project.state == region) and (not market or project.market == market)
                ]
            ),
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
        "status": "New",
        "next_action": "Follow up with developer",
    }
    new_project["score"] = calculate_score(new_project)
    projects.append(new_project)
    save_projects(projects)
    discovery_engine.mark_imported(project_name)

    return render_template(
        "discover_projects.html",
        discover_projects=serialize_discovery_projects(
            [
                project for project in load_discover_projects()
                if (not region or project.state == region) and (not market or project.market == market)
            ]
        ),
        region=region,
        market=market,
        message=f"{project_name} imported successfully.",
        active_page="discover",
    )


@app.route("/contacts")
def contacts_page():
    return render_template("page.html", title="Contacts", content="Contacts page coming soon.", active_page="contacts")


@app.route("/tasks")
def tasks_page():
    return render_template("page.html", title="Tasks", content="Tasks page coming soon.", active_page="tasks")


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
    projects = load_projects()
    project = next((item for item in projects if item.get("id") == project_id), None)

    if project is None:
        return "Project not found", 404

    return render_template("project.html", project=project, active_page="dashboard")


@app.route("/project/<int:project_id>/research")
def project_research(project_id):
    projects = load_projects()
    project = next((item for item in projects if item.get("id") == project_id), None)

    if project is None:
        return "Project not found", 404

    return render_template("research.html", project=project, active_page="dashboard")


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