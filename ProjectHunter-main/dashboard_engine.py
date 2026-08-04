"""Pure calculations for Mission Control's daily sales command center."""

from datetime import date, datetime, timezone


STAGE_SCORES = {
    "active construction": 100,
    "awarded": 90,
    "bidding": 80,
    "preconstruction": 70,
    "needs research": 35,
    "new": 30,
}


def parse_date(value):
    """Return a timezone-aware datetime for feed dates we can safely interpret."""
    if not value or "Q" in str(value).upper():
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (TypeError, ValueError):
        return None


def relative_time(value, now=None):
    parsed = parse_date(value)
    if parsed is None:
        return str(value or "Date unavailable")
    now = now or datetime.now(timezone.utc)
    days = max(0, (now - parsed).days)
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    months = days // 30
    return f"{months} month{'s' if months != 1 else ''} ago"


def project_company(project):
    return (project.get("electrical_contractor") or project.get("general_contractor")
            or project.get("developer") or "Company not identified")


def _contacts_for_project(project, contacts):
    companies = {str(project.get(field) or "").casefold() for field in
                 ("electrical_contractor", "general_contractor", "developer")}
    return [contact for contact in contacts if str(contact.get("company") or "").casefold() in companies]


def priority_score(project, contacts, today=None):
    """Score 0-100 using the six documented queue signals."""
    today = today or date.today()
    confidence = min(100, max(0, int(project.get("confidence") or 0)))
    stage = STAGE_SCORES.get(str(project.get("current_stage") or "").casefold(), 50)
    activity = parse_date(project.get("last_activity"))
    age = max(0, (today - activity.date()).days) if activity else 30
    recency = max(0, 100 - age * 5)
    contractor = 100 if project.get("electrical_contractor") else 0
    related_contacts = _contacts_for_project(project, contacts)
    contact_availability = 100 if any(item.get("ready_to_email") for item in related_contacts) else (50 if related_contacts else 0)
    follow_up_due = 100 if age >= 7 or any(item.get("outreach_status") in {"Email opened", "Email sent"} for item in related_contacts) else 25
    score = round(confidence * .30 + stage * .20 + recency * .15 + contractor * .15 + follow_up_due * .10 + contact_availability * .10)
    return min(100, max(0, score))


def build_priorities(projects, contacts):
    items = []
    for project in projects:
        item = dict(project)
        item["priority_score"] = priority_score(project, contacts)
        item["company"] = project_company(project)
        items.append(item)
    return sorted(items, key=lambda item: (-item["priority_score"], -int(item.get("confidence") or 0), item["name"]))


def build_follow_ups(projects, contacts, dismissed=None, today=None):
    dismissed, today = dismissed or set(), today or date.today()
    tasks = []
    for project in projects:
        activity = parse_date(project.get("last_activity"))
        age = max(0, (today - activity.date()).days) if activity else 30
        related = _contacts_for_project(project, contacts)
        reasons = []
        if age >= 7:
            reasons.append(("no-activity", "No activity in 7 days", today))
        if any(c.get("outreach_status") == "Email opened" for c in related) and not any(c.get("outreach_status") == "Email replied" for c in related):
            reasons.append(("opened-no-reply", "Email opened but no reply", today))
        if project.get("electrical_contractor") and not related:
            reasons.append(("contractor-no-contacts", "Contractor confirmed but no contacts", today))
        if project.get("current_stage") == "Needs Research" or not project.get("electrical_contractor"):
            reasons.append(("research-incomplete", "Research incomplete", today))
        for kind, reason, due in reasons:
            task_id = f"{project['id']}-{kind}"
            if task_id not in dismissed:
                tasks.append({"id": task_id, "project": project, "reason": reason, "due_date": due, "priority_score": priority_score(project, contacts)})
    return sorted(tasks, key=lambda item: (-item["priority_score"], item["project"]["name"]))


def build_activity(projects, contacts):
    feed = []
    for project in projects:
        timestamp = project.get("last_activity")
        feed.append({"type": "Intelligence update", "text": f"Intelligence updated for {project['name']}", "timestamp": timestamp, "project": project})
        feed.append({"type": "Project added", "text": project["name"], "timestamp": timestamp, "project": project})
        if project.get("electrical_contractor"):
            feed.append({"type": "Contractor confirmed", "text": project["electrical_contractor"], "timestamp": timestamp, "project": project})
        for event in project.get("timeline", []):
            name = str(event.get("event") or "Intelligence update")
            event_type = next((kind for kind in ("Email sent", "Email opened", "Email replied", "Bounce detected", "Follow-up completed") if kind.casefold() in name.casefold()), "Intelligence update")
            feed.append({"type": event_type, "text": name, "timestamp": event.get("date"), "project": project})
    for index, contact in enumerate(contacts, 1):
        timestamp = contact.get("last_contacted") or contact.get("imported_at")
        feed.append({"type": "Contact imported", "text": f"{contact.get('name')} · {contact.get('company')}", "timestamp": timestamp, "contact_id": index})
        status = contact.get("outreach_status")
        if status in {"Email sent", "Email opened", "Email replied", "Follow-up completed"}:
            feed.append({"type": status, "text": f"{contact.get('name')} · {contact.get('company')}", "timestamp": timestamp, "contact_id": index})
        if contact.get("email_status") == "Bounced":
            feed.append({"type": "Bounce detected", "text": f"{contact.get('name')} · {contact.get('email')}", "timestamp": timestamp, "contact_id": index})
    for event in feed:
        event["relative_time"] = relative_time(event["timestamp"])
        event["sort_date"] = parse_date(event["timestamp"]) or datetime.min.replace(tzinfo=timezone.utc)
    return sorted(feed, key=lambda item: item["sort_date"], reverse=True)


def calculate_revenue(projects):
    """Single source of truth for Revenue Engine formulas."""
    rows = []
    for project in projects:
        potential = float(project.get("estimated_revenue") or 0)
        confidence = min(100, max(0, int(project.get("confidence") or 0)))
        rows.append({"project": project, "potential": potential, "confidence": confidence,
                     "weighted": potential * confidence / 100})
    potential = sum(row["potential"] for row in rows)
    weighted = sum(row["weighted"] for row in rows)
    confidence = round(weighted / potential * 100) if potential else 0
    return {"potential": potential, "weighted": weighted, "confidence": confidence, "rows": rows,
            "potential_formula": "Sum of project estimated revenue",
            "weighted_formula": "Each project estimate × its confidence",
            "confidence_formula": "Weighted revenue ÷ potential revenue"}
