"""Runtime store for the curated Arizona sales intelligence feed."""

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


INTELLIGENCE_PATH = Path(__file__).resolve().parent / "data" / "arizona_intelligence.json"
HIGH_PRIORITY_THRESHOLD = 90
KNOWN_HELIX_BOUNCES = {
    "r.measles@helixelectric.com",
    "b.trunkey@helixelectric.com",
    "l.jones@helixelectric.com",
}


class IntelligenceStore:
    """Load, normalize, and retain intelligence until an explicit sync."""

    def __init__(self, path=INTELLIGENCE_PATH):
        self.path = Path(path)
        self._data = None
        self.last_updated = None

    def reload(self):
        with self.path.open(encoding="utf-8") as handle:
            raw = json.load(handle)

        projects = []
        for project_id, (key, project) in enumerate(raw.get("projects", {}).items(), 1):
            normalized = deepcopy(project)
            normalized.update({"id": project_id, "key": key})
            projects.append(normalized)

        contacts_by_email = {}
        for raw_contact in raw.get("contacts", []):
            contact = deepcopy(raw_contact)
            email = str(contact.get("email", "")).strip().lower()
            if not email or email in contacts_by_email:
                continue
            contact["email"] = email
            if email in KNOWN_HELIX_BOUNCES:
                contact["email_status"] = "Bounced"
            contact.setdefault("outreach_status", "Not contacted")
            contact.setdefault("last_contacted", "")
            contact.setdefault("notes", "")
            contact["ready_to_email"] = contact.get("email_status") != "Bounced"
            contacts_by_email[email] = contact

        contacts = sorted(
            contacts_by_email.values(),
            key=lambda item: (-int(item.get("priority", 0)), item.get("name", "").lower()),
        )
        self._data = {"projects": projects, "contacts": contacts}
        self.last_updated = datetime.now(timezone.utc)
        return self.snapshot()

    def snapshot(self):
        if self._data is None:
            self.reload()
        return deepcopy(self._data)

    def metrics(self):
        data = self.snapshot()
        contractors = [candidate for project in data["projects"] for candidate in project.get("contractors", [])]
        return {
            "total_projects": len(data["projects"]),
            "confirmed_contractors": sum(
                str(candidate.get("status", "")).lower().startswith("confirmed") for candidate in contractors
            ),
            "projects_needing_research": sum(
                not any(
                    str(candidate.get("status", "")).lower() == "confirmed"
                    and "electrical" in str(candidate.get("trade", "")).lower()
                    for candidate in project.get("contractors", [])
                )
                for project in data["projects"]
            ),
            "total_contacts": len(data["contacts"]),
            "verified_contacts": sum(contact.get("email_status") == "Verified" for contact in data["contacts"]),
            "bounced_contacts": sum(contact.get("email_status") == "Bounced" for contact in data["contacts"]),
            "high_priority_contacts": sum(
                int(contact.get("priority", 0)) >= HIGH_PRIORITY_THRESHOLD for contact in data["contacts"]
            ),
        }

    @property
    def source_label(self):
        return str(self.path.relative_to(Path(__file__).resolve().parent))


intelligence_store = IntelligenceStore()
