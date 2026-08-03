from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parents[1]
INTELLIGENCE_PATH = BASE_DIR / "data" / "arizona_intelligence.json"


def load_intelligence() -> Dict[str, Any]:
    if not INTELLIGENCE_PATH.exists():
        return {"projects": {}, "contacts": []}
    with INTELLIGENCE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize(value: str) -> str:
    return " ".join(str(value or "").lower().replace("/", " ").replace("-", " ").split())


def find_project_intelligence(project_name: str) -> Dict[str, Any] | None:
    intelligence = load_intelligence()
    projects = intelligence.get("projects", {})
    normalized = _normalize(project_name)

    for key, record in projects.items():
        normalized_key = _normalize(key)
        display_name = _normalize(record.get("display_name", ""))
        if normalized_key in normalized or normalized in normalized_key or display_name in normalized or normalized in display_name:
            return record
    return None


def get_contacts(company_names: List[str] | None = None) -> List[Dict[str, Any]]:
    contacts = load_intelligence().get("contacts", [])
    if company_names:
        wanted = {_normalize(name) for name in company_names if name}
        contacts = [contact for contact in contacts if _normalize(contact.get("company", "")) in wanted]
    return sorted(contacts, key=lambda item: (-int(item.get("priority", 0)), item.get("name", "")))


def build_project_research(project: Dict[str, Any]) -> Dict[str, Any]:
    record = find_project_intelligence(project.get("name", ""))
    if not record:
        return {"record": None, "contractors": [], "contacts": [], "next_action": project.get("next_action", "Research contractor")}

    contractors = record.get("contractors", [])
    company_names = [item.get("company", "") for item in contractors]
    contacts = get_contacts(company_names)
    return {
        "record": record,
        "contractors": contractors,
        "contacts": contacts,
        "next_action": record.get("next_action") or project.get("next_action", "Research contractor"),
    }


def build_actionable_opportunities() -> List[Dict[str, Any]]:
    """Build outreach-ready project rows from saved intelligence."""
    intelligence = load_intelligence()
    opportunities: List[Dict[str, Any]] = []
    for key, record in intelligence.get("projects", {}).items():
        for contractor in record.get("contractors", []):
            company = contractor.get("company", "")
            contacts = get_contacts([company])
            if not contacts:
                continue
            opportunities.append({
                "key": key,
                "project": record.get("display_name") or key.title(),
                "developer": record.get("developer", "Unknown"),
                "general_contractor": record.get("general_contractor", "Unknown"),
                "contractor": company,
                "trade": contractor.get("trade", "Contractor"),
                "status": contractor.get("status", "Research"),
                "confidence": int(contractor.get("confidence", 0) or 0),
                "reason": contractor.get("reason", ""),
                "contact_count": len(contacts),
                "best_contact": contacts[0],
                "contacts": contacts,
                "next_action": record.get("next_action", "Contact the project team"),
                "evidence": contractor.get("evidence", []),
            })
    return sorted(opportunities, key=lambda row: (-row["confidence"], -row["best_contact"].get("priority", 0)))


def build_contractor_campaigns() -> List[Dict[str, Any]]:
    """Build company-level campaigns for qualified contacts not yet tied to a confirmed project."""
    contacts = get_contacts()
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for contact in contacts:
        grouped.setdefault(contact.get("company", "Unknown"), []).append(contact)

    campaigns = []
    for company, company_contacts in grouped.items():
        campaigns.append({
            "company": company,
            "contact_count": len(company_contacts),
            "best_contact": company_contacts[0],
            "contacts": company_contacts,
            "market": "Arizona data centers",
            "relationship": "Qualified market target; specific project award may be unconfirmed",
        })
    return sorted(campaigns, key=lambda row: (-row["best_contact"].get("priority", 0), row["company"]))
