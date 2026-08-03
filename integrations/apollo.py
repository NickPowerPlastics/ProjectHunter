from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import error, request

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency missing
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

if load_dotenv is not None:
    load_dotenv(dotenv_path=ENV_PATH, override=False)


@dataclass
class ApolloCompanyProfile:
    company_name: str
    website: str
    headquarters: str
    employee_count: str
    industry: str
    revenue_range: str
    number_of_contacts: int
    last_updated: str


@dataclass
class ApolloContact:
    name: str
    title: str
    company: str
    location: str
    email_status: str
    person_id: str
    linkedin_url: str
    business_email: Optional[str] = None
    retrieval_date: Optional[str] = None


class ApolloCompanyService:
    TARGET_TITLES = [
        "Preconstruction Manager",
        "Chief Estimator",
        "Senior Estimator",
        "Purchasing Manager",
        "Procurement Manager",
        "Project Executive",
        "Electrical Project Manager",
        "Project Manager",
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("APOLLO_API_KEY")
        self.base_url = os.getenv("APOLLO_BASE_URL", "https://api.apollo.io/v1/people/search")
        self.use_mock_fallback = os.getenv("APOLLO_USE_MOCK_FALLBACK", "").lower() in {"1", "true", "yes", "on"}
        self.connection_status = "Not attempted"
        self.last_connection_attempt = None
        self.last_successful_connection = None

    def lookup_company(self, company_name: str) -> ApolloCompanyProfile:
        if self.api_key:
            return self._fetch_company_from_api(company_name)
        if self.use_mock_fallback:
            return self._mock_profile(company_name)
        raise RuntimeError("APOLLO_API_KEY is not configured. Set it in the environment to enable live Apollo lookups.")

    def search_contacts(self, company_name: str, state: str) -> List[ApolloContact]:
        self.last_connection_attempt = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if not self.api_key:
            self.connection_status = "Missing API key"
            if self.use_mock_fallback:
                return self._mock_contacts(company_name=company_name, state=state)
            raise RuntimeError("APOLLO_API_KEY is not configured. Set APOLLO_API_KEY in your environment to enable live Apollo contact search.")

        try:
            self.connection_status = "Connected"
            return self._fetch_contacts_from_api(company_name=company_name, state=state)
        except RuntimeError as exc:
            self.connection_status = str(exc)
            raise RuntimeError(f"Apollo contact search failed: {exc}") from exc

    def test_connection(self) -> Dict[str, Any]:
        self.last_connection_attempt = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if not self.api_key:
            self.connection_status = "Missing API key"
            return {
                "connected": False,
                "company_accessible": False,
                "response_time_ms": None,
                "rate_limit": None,
                "error_message": "APOLLO_API_KEY is not configured. Add it to your environment or .env file.",
                "error_status_code": None,
            }

        try:
            start = datetime.now(timezone.utc)
            response_data = self._request_json(
                {
                    "q_organization_name": "Apollo",
                    "page": 1,
                    "per_page": 1,
                    "enrich": False,
                },
                timeout=5,
            )
            response_time_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
            self.connection_status = "Connected"
            self.last_successful_connection = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            return {
                "connected": True,
                "company_accessible": True,
                "response_time_ms": response_time_ms,
                "rate_limit": self._extract_rate_limit(response_data),
                "error_message": None,
                "error_status_code": None,
            }
        except RuntimeError as exc:
            self.connection_status = str(exc)
            error_status_code = self._extract_status_code(str(exc))
            return {
                "connected": False,
                "company_accessible": False,
                "response_time_ms": None,
                "rate_limit": None,
                "error_message": self._humanize_error(str(exc)),
                "error_status_code": error_status_code,
            }

    def _mock_profile(self, company_name: str) -> ApolloCompanyProfile:
        return ApolloCompanyProfile(
            company_name=company_name or "Unknown Company",
            website="https://example.com",
            headquarters="Remote / Not listed",
            employee_count="201-500",
            industry="Mission Critical / Data Center",
            revenue_range="$10M-$50M",
            number_of_contacts=3,
            last_updated=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        )

    def _mock_contacts(self, company_name: str, state: str) -> List[ApolloContact]:
        return [
            ApolloContact(
                name="Apollo Contact",
                title="Preconstruction Manager",
                company=company_name or "Unknown Company",
                location=state,
                email_status="unavailable",
                person_id="apollo-mock",
                linkedin_url="https://www.linkedin.com",
                business_email=None,
                retrieval_date=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            )
        ]

    def _fetch_company_from_api(self, company_name: str) -> ApolloCompanyProfile:
        return self._mock_profile(company_name)

    def _fetch_contacts_from_api(self, company_name: str, state: str) -> List[ApolloContact]:
        payload = {
            "q_organization_name": company_name,
            "person_titles": self.TARGET_TITLES,
            "person_locations": [state] if state else [],
            "per_page": 10,
            "page": 1,
            "enrich": False,
        }
        response_data = self._request_json(payload)
        contacts = response_data.get("contacts") if isinstance(response_data, dict) else None
        if not contacts and isinstance(response_data, dict):
            contacts = response_data.get("people") or response_data.get("results") or []

        ranked_contacts: List[ApolloContact] = []
        for item in contacts or []:
            normalized = self._normalize_contact(item, company_name=company_name, state=state)
            if normalized is None:
                continue
            ranked_contacts.append(normalized)

        ranked_contacts = sorted(ranked_contacts, key=self._contact_rank, reverse=True)
        return ranked_contacts[:5]

    def _normalize_contact(self, item: Any, company_name: str, state: str) -> Optional[ApolloContact]:
        if isinstance(item, ApolloContact):
            return item

        if not isinstance(item, dict):
            return None

        title = str(item.get("title") or item.get("job_title") or item.get("person_title") or "").strip()
        if not title:
            title = "Unknown"

        email_value = item.get("business_email") or item.get("email") or item.get("email_address")
        email_status = self._normalize_email_status(email_value, item.get("email_status"))
        location = self._select_location(item, state)
        person_id = str(item.get("id") or item.get("person_id") or item.get("contact_id") or "")
        linkedin_url = str(item.get("linkedin_url") or item.get("linkedin") or "")
        business_email = str(email_value).strip() if email_value else None

        return ApolloContact(
            name=str(item.get("name") or item.get("full_name") or "Unknown Contact").strip(),
            title=title,
            company=str(item.get("company_name") or item.get("company") or company_name or "Unknown Company").strip(),
            location=location,
            email_status=email_status,
            person_id=person_id,
            linkedin_url=linkedin_url,
            business_email=business_email,
            retrieval_date=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        )

    def _contact_rank(self, contact: ApolloContact) -> int:
        title = (contact.title or "").lower()
        if "preconstruction" in title:
            return 100
        if "chief" in title or "senior" in title or "estimator" in title:
            return 90
        if "purchasing" in title or "procurement" in title:
            return 80
        if "project executive" in title:
            return 70
        if "electrical project manager" in title:
            return 60
        if "project manager" in title:
            return 50
        return 10

    def _select_location(self, item: Dict[str, Any], state: str) -> str:
        city = str(item.get("city") or item.get("location") or "").strip()
        region = str(item.get("state") or item.get("region") or state or "").strip()
        if city and region:
            return f"{city}, {region}"
        if city:
            return city
        if region:
            return region
        return state or "Unknown"

    def _normalize_email_status(self, email_value: Optional[str], api_status: Optional[str]) -> str:
        if not email_value:
            return "unavailable"
        status = str(api_status or "").strip().lower()
        if status == "verified":
            return "verified"
        if status in {"extrapolated", "available", "unverified"}:
            return "extrapolated"
        return "extrapolated"

    def _request_json(self, payload: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(self.base_url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw) if raw else {}
                if not isinstance(parsed, dict):
                    parsed = {"data": parsed}
                parsed["headers"] = {
                    key: value for key, value in response.headers.items()
                }
                return parsed
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            message = detail or f"Apollo API rejected the request with status {exc.code}"
            raise RuntimeError(f"{exc.code}: {message}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Unable to reach Apollo API: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError("Apollo API request timed out") from exc

    def _extract_rate_limit(self, response_data: Dict[str, Any]) -> Optional[str]:
        if not isinstance(response_data, dict):
            return None
        headers = response_data.get("headers")
        if isinstance(headers, dict):
            remaining = headers.get("x-ratelimit-remaining") or headers.get("X-RateLimit-Remaining")
            if remaining:
                return str(remaining)
        return None

    def _extract_status_code(self, message: str) -> Optional[int]:
        try:
            first_number = message.split(":", 1)[0].strip()
            if first_number.isdigit():
                return int(first_number)
            return int(message.rsplit("status", 1)[-1].strip())
        except ValueError:
            return None

    def _humanize_error(self, message: str) -> str:
        lowered = message.lower()
        if "401" in lowered or "unauthorized" in lowered:
            return "Authentication failed. Verify that APOLLO_API_KEY is valid."
        if "403" in lowered or "forbidden" in lowered:
            return "Apollo rejected the request. Confirm the key has permission for this endpoint."
        if "429" in lowered:
            return "Apollo rate limit reached. Please wait before retrying."
        if "timed out" in lowered:
            return "The Apollo request timed out. Please try again shortly."
        return "Apollo could not be reached or rejected the request."
