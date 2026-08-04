"""JSON-backed, state-agnostic intelligence model for Project Hunter."""

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


INTELLIGENCE_PATH = Path(__file__).resolve().parent / "data" / "intelligence.json"
KNOWN_HELIX_BOUNCES = {
    "r.measles@helixelectric.com", "b.trunkey@helixelectric.com", "l.jones@helixelectric.com"
}


def _money(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


class IntelligenceStore:
    """Load and normalize the complete feed without hard-coded states or companies."""

    def __init__(self, path=INTELLIGENCE_PATH):
        self.path = Path(path)
        self._data = None
        self.last_updated = None

    def reload(self):
        with self.path.open(encoding="utf-8") as handle:
            raw = json.load(handle)

        source_projects = raw.get("projects", {})
        items = source_projects.items() if isinstance(source_projects, dict) else (
            (str(item.get("key") or item.get("name") or position), item)
            for position, item in enumerate(source_projects, 1)
        )
        projects = []
        for project_id, (key, source) in enumerate(items, 1):
            project = deepcopy(source)
            project["id"] = project_id
            project["key"] = key
            project.setdefault("name", project.get("display_name") or key.title())
            project.setdefault("display_name", project["name"])
            project.setdefault("state", "Unassigned")
            project.setdefault("current_stage", project.get("status") or "Needs Research")
            project.setdefault("status", project["current_stage"])
            project.setdefault("confidence", max(
                [int(candidate.get("confidence", 0) or 0) for candidate in project.get("contractors", [])] or [0]
            ))
            project.setdefault("evidence", [
                evidence for contractor in project.get("contractors", []) for evidence in contractor.get("evidence", [])
            ])
            project.setdefault("recommended_next_action", project.get("next_action") or "Research project team")
            project.setdefault("next_action", project["recommended_next_action"])
            project.setdefault("timeline", [])
            project.setdefault("associated_contacts", [])
            project.setdefault("estimated_revenue", 0)
            project.setdefault("last_activity", raw.get("updated_at", ""))
            projects.append(project)

        contacts_by_email = {}
        for source in raw.get("contacts", []):
            contact = deepcopy(source)
            email = str(contact.get("email", "")).strip().lower()
            identity = email or f"{contact.get('name', '')}|{contact.get('company', '')}".lower()
            if not identity or identity in contacts_by_email:
                continue
            contact["email"] = email
            contact["id"] = len(contacts_by_email) + 1
            if email in KNOWN_HELIX_BOUNCES:
                contact["email_status"] = "Bounced"
            contact.setdefault("outreach_status", "Not contacted")
            contact.setdefault("last_contacted", "")
            contact.setdefault("notes", "")
            contact["ready_to_email"] = bool(email) and contact.get("email_status") != "Bounced"
            contacts_by_email[identity] = contact
        contacts = sorted(contacts_by_email.values(), key=lambda item: (-int(item.get("priority", 0)), item.get("name", "").lower()))

        self._data = {"projects": projects, "contacts": contacts, "updated_at": raw.get("updated_at", "")}
        self.last_updated = datetime.now(timezone.utc)
        return self.snapshot()

    def snapshot(self):
        if self._data is None:
            self.reload()
        return deepcopy(self._data)

    def companies(self):
        data = self.snapshot()
        contacts_by_company = {}
        for contact in data["contacts"]:
            contacts_by_company.setdefault(str(contact.get("company", "")).casefold(), []).append(contact)
        companies = {}
        roles = (
            ("developer", "Developer"), ("general_contractor", "General Contractor"),
            ("electrical_contractor", "Electrical Contractor"), ("mechanical_contractor", "Mechanical Contractor"),
        )
        for project in data["projects"]:
            for field, company_type in roles:
                name = str(project.get(field) or "").strip()
                if not name or name.lower() in {"unknown", "tbd", "not identified"}:
                    continue
                key = name.casefold()
                company = companies.setdefault(key, {
                    "name": name, "types": [], "projects": [], "contacts": contacts_by_company.get(key, []),
                    "estimated_opportunity": 0.0, "last_activity": "", "contractor_confidence": 0, "open_tasks": 0,
                })
                if company_type not in company["types"]:
                    company["types"].append(company_type)
                if project["id"] not in [item["id"] for item in company["projects"]]:
                    company["projects"].append(project)
                    company["estimated_opportunity"] += _money(project.get("estimated_revenue"))
                    company["contractor_confidence"] = max(company["contractor_confidence"], int(project.get("confidence", 0)))
                    company["open_tasks"] += project.get("current_stage") == "Needs Research"
                    company["last_activity"] = max(company["last_activity"], str(project.get("last_activity", "")))
        result = sorted(companies.values(), key=lambda item: item["name"].casefold())
        for company_id, company in enumerate(result, 1):
            company["id"] = company_id
            company["type"] = " / ".join(company["types"])
        return result

    def states(self):
        grouped = {}
        for project in self.snapshot()["projects"]:
            grouped.setdefault(project.get("state") or "Unassigned", []).append(project)
        return [{"name": state, "projects": sorted(projects, key=lambda item: item["name"].casefold())}
                for state, projects in sorted(grouped.items())]

    def metrics(self):
        data = self.snapshot()
        companies = self.companies()
        confirmed = [p for p in data["projects"] if p.get("electrical_contractor") and p.get("confidence", 0) >= 80]
        needs_research = [p for p in data["projects"] if p.get("current_stage") == "Needs Research" or not p.get("electrical_contractor")]
        return {
            "projects": len(data["projects"]), "companies": len(companies), "contacts": len(data["contacts"]),
            "states": len(self.states()), "confirmed_contractors": len(confirmed), "needs_research": len(needs_research),
            "emails_sent": sum(c.get("outreach_status") == "Email sent" for c in data["contacts"]),
            "opportunities": sum(_money(p.get("estimated_revenue")) > 0 for p in data["projects"]),
            "estimated_pipeline": sum(_money(p.get("estimated_revenue")) for p in data["projects"]),
        }

    @property
    def source_label(self):
        return str(self.path.relative_to(Path(__file__).resolve().parent))


intelligence_store = IntelligenceStore()
