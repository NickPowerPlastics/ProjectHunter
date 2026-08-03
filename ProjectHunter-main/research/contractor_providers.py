from __future__ import annotations

from typing import Any, Dict, List

from .contractor_provider import ContractorResearchProvider


class MockContractorResearchProvider(ContractorResearchProvider):
    name = "mock"

    def run(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        project_name = str(project.get("name") or "").strip()
        city = str(project.get("state") or "").strip()
        developer = str(project.get("developer") or "").strip()
        general_contractor = str(project.get("general_contractor") or "").strip()

        return [
            {
                "candidate_name": f"{project_name} Electrical Team" if project_name else "North Star Electric",
                "confidence_score": 91,
                "source_url": "https://example.com/contractor-search",
                "evidence_snippet": f"Matches {developer or general_contractor or city} and mission critical electrical work",
            },
            {
                "candidate_name": "Blue Ridge Power",
                "confidence_score": 78,
                "source_url": "https://example.com/contractor-search-2",
                "evidence_snippet": f"Active in {city or 'regional'} data center electrical installations",
            },
            {
                "candidate_name": "Mission Critical Electric",
                "confidence_score": 72,
                "source_url": "https://example.com/contractor-search-3",
                "evidence_snippet": "Known for high-density power distribution and critical facilities",
            },
        ]


class WebContractorResearchProvider(ContractorResearchProvider):
    name = "web"

    def run(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []
