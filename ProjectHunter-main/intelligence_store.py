"""JSON-backed, state-agnostic intelligence model for Project Hunter."""

import json
import os
import shutil
import tempfile
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path


INTELLIGENCE_PATH = Path(__file__).resolve().parent / "data" / "intelligence.json"
KNOWN_HELIX_BOUNCES = {
    "r.measles@helixelectric.com", "b.trunkey@helixelectric.com", "l.jones@helixelectric.com"
}


class IntelligenceValidationError(ValueError):
    """Raised when an imported intelligence feed is not safe to load."""


def _validate_number(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise IntelligenceValidationError(f"{label} must be numeric.") from error
    if number != number or number in (float("inf"), float("-inf")):
        raise IntelligenceValidationError(f"{label} must be a finite number.")


def _reject_json_constant(value):
    raise IntelligenceValidationError(f"Invalid JSON number: {value}.")


def _parse_feed_date(value):
    if not isinstance(value, str) or not value.strip():
        raise IntelligenceValidationError("updated_at is required and must be an ISO-8601 date or timestamp.")
    candidate = value.strip()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        return parsed.date()
    except ValueError:
        try:
            return date.fromisoformat(candidate)
        except ValueError as error:
            raise IntelligenceValidationError(
                "updated_at is required and must be an ISO-8601 date or timestamp."
            ) from error


def validate_intelligence_payload(payload):
    """Validate the stable, intentionally small contract consumed by IntelligenceStore."""
    if not isinstance(payload, dict):
        raise IntelligenceValidationError("The feed must be a JSON object.")
    _parse_feed_date(payload.get("updated_at"))

    projects = payload.get("projects")
    if not isinstance(projects, (dict, list)):
        raise IntelligenceValidationError("projects must be an object or an array.")
    project_items = list(projects.values()) if isinstance(projects, dict) else projects
    for position, project in enumerate(project_items, 1):
        if not isinstance(project, dict):
            raise IntelligenceValidationError(f"Project {position} must be a JSON object.")
        if not str(project.get("name") or project.get("display_name") or "").strip():
            raise IntelligenceValidationError(f"Project {position} must include name or display_name.")
        if "contractors" in project and not isinstance(project["contractors"], list):
            raise IntelligenceValidationError(f"Project {position} contractors must be an array.")
        if "timeline" in project and not isinstance(project["timeline"], list):
            raise IntelligenceValidationError(f"Project {position} timeline must be an array.")
        if "evidence" in project and not isinstance(project["evidence"], list):
            raise IntelligenceValidationError(f"Project {position} evidence must be an array.")
        for field in ("confidence", "estimated_revenue"):
            if field in project:
                _validate_number(project[field], f"Project {position} {field}")
        for contractor_position, contractor in enumerate(project.get("contractors", []), 1):
            if not isinstance(contractor, dict):
                raise IntelligenceValidationError(
                    f"Project {position} contractor {contractor_position} must be a JSON object."
                )
            if "confidence" in contractor:
                _validate_number(
                    contractor["confidence"], f"Project {position} contractor {contractor_position} confidence"
                )
            if "evidence" in contractor and not isinstance(contractor["evidence"], list):
                raise IntelligenceValidationError(
                    f"Project {position} contractor {contractor_position} evidence must be an array."
                )

    contacts = payload.get("contacts")
    if not isinstance(contacts, list):
        raise IntelligenceValidationError("contacts must be an array.")
    for position, contact in enumerate(contacts, 1):
        if not isinstance(contact, dict):
            raise IntelligenceValidationError(f"Contact {position} must be a JSON object.")
        if not str(contact.get("name") or contact.get("email") or "").strip():
            raise IntelligenceValidationError(f"Contact {position} must include name or email.")
        if "email" in contact and not isinstance(contact["email"], str):
            raise IntelligenceValidationError(f"Contact {position} email must be a string.")
        if "priority" in contact:
            _validate_number(contact["priority"], f"Contact {position} priority")
    return payload


def parse_intelligence_json(text):
    try:
        payload = json.loads(text, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, TypeError) as error:
        detail = getattr(error, "msg", "Invalid JSON")
        raise IntelligenceValidationError(f"Invalid JSON: {detail}.") from error
    return validate_intelligence_payload(payload)


def preview_intelligence_payload(payload):
    validate_intelligence_payload(payload)
    projects = list(payload["projects"].values()) if isinstance(payload["projects"], dict) else payload["projects"]
    state_counts = {}
    for project in projects:
        state = str(project.get("state") or "Unassigned").strip() or "Unassigned"
        state_counts[state] = state_counts.get(state, 0) + 1
    return {
        "updated_at": payload["updated_at"],
        "project_count": len(projects),
        "contact_count": len(payload["contacts"]),
        "state_count": len(state_counts),
        "states": sorted(state_counts.items()),
        "projects": [str(project.get("name") or project.get("display_name")) for project in projects],
        "contacts": [str(contact.get("name") or contact.get("email")) for contact in payload["contacts"]],
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

    def replace(self, payload):
        """Back up and atomically replace the feed, then reload the in-memory store."""
        validate_intelligence_payload(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        backup_path = None
        if self.path.exists():
            backup_dir = self.path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup_path = backup_dir / f"intelligence-{stamp}.json"
            shutil.copy2(self.path, backup_path)

        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent, prefix=".intelligence-", suffix=".tmp", delete=False
            ) as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
                temporary_path = Path(handle.name)
            os.replace(temporary_path, self.path)
            temporary_path = None
            self.reload()
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()
        return backup_path

    def freshness(self, now=None, stale_after_days=3):
        snapshot = self.snapshot()
        feed_date = _parse_feed_date(snapshot.get("updated_at"))
        today = (now or datetime.now(timezone.utc)).date()
        age_days = max((today - feed_date).days, 0)
        return {
            "feed_date": feed_date.isoformat(),
            "age_days": age_days,
            "stale_after_days": stale_after_days,
            "is_stale": age_days > stale_after_days,
        }

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
        try:
            return str(self.path.relative_to(Path(__file__).resolve().parent))
        except ValueError:
            return self.path.name


intelligence_store = IntelligenceStore()
