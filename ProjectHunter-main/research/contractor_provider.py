from __future__ import annotations

import os
from typing import Any, Dict, List


class ContractorResearchProvider:
    name = "contractor"

    def build_queries(self, project: Dict[str, Any]) -> List[str]:
        project_name = str(project.get("name") or "").strip()
        city = str(project.get("state") or "").strip()
        developer = str(project.get("developer") or "").strip()
        general_contractor = str(project.get("general_contractor") or "").strip()
        terms = [
            "electrical contractor",
            "electrical subcontractor",
            "mission critical",
            "data center",
        ]

        queries = []
        parts = [project_name, city, developer, general_contractor]
        for part in [p for p in parts if p]:
            for term in terms:
                queries.append(f'"{part}" {term}')
        if project_name:
            queries.append(f'{project_name} electrical contractor')
        if city and developer:
            queries.append(f'{developer} {city} electrical contractor')
        if general_contractor and city:
            queries.append(f'{general_contractor} {city} electrical subcontractor')
        return queries[:8]

    def search(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []

    def run(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        if os.getenv("SEARCH_API_URL"):
            return self.search(project)
        return []
