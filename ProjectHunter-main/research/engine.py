from __future__ import annotations

from typing import Any, Dict, List

from .contractor_provider import ContractorResearchProvider
from .contractor_providers import MockContractorResearchProvider, WebContractorResearchProvider
from .provider import ResearchProvider
from .providers import MockResearchProvider, WebResearchProvider


class ResearchEngine:
    def __init__(self, providers: List[ResearchProvider] | None = None, contractor_providers: List[ContractorResearchProvider] | None = None):
        self.providers = providers or [MockResearchProvider(), WebResearchProvider()]
        self.contractor_providers = contractor_providers or [MockContractorResearchProvider(), WebContractorResearchProvider()]

    def run(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for provider in self.providers:
            results.extend(provider.research(project))
        return results

    def run_contractor_research(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        for provider in self.contractor_providers:
            candidates.extend(provider.run(project))
        return candidates[:3]
