from __future__ import annotations

from typing import Any, Dict, List

from .provider import ResearchProvider


class MockResearchProvider(ResearchProvider):
    name = "mock"

    def research(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {
                "section": "Project Overview",
                "content": "Initial outreach",
            },
            {
                "section": "Developer",
                "content": "No research available yet.",
            },
        ]


class WebResearchProvider(ResearchProvider):
    name = "web"

    def research(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []
