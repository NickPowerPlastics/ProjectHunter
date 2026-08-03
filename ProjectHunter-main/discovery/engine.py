from __future__ import annotations

from typing import List

from .models import Project
from .provider import DiscoveryProvider
from .providers import DataCenterDynamicsProvider, MockProvider
from .sources import DiscoverySource


class DiscoveryEngine:
    def __init__(self, source: DiscoverySource | None = None, providers: List[DiscoveryProvider] | None = None):
        self.source = source or DiscoverySource()
        self.providers = providers or [MockProvider(), DataCenterDynamicsProvider()]

    def run(self, region: str = "Arizona", market: str = "Data Centers") -> List[Project]:
        projects: List[Project] = []
        for provider in self.providers:
            projects.extend(provider.discover(region, market))
        self.source.save(projects)
        return projects

    def load(self) -> List[Project]:
        projects = self.source.load()
        if not projects:
            return self.run()
        return projects

    def mark_imported(self, project_name: str) -> bool:
        projects = self.load()
        for project in projects:
            if project.project_name.lower() == project_name.lower():
                project.imported = True
                self.source.save(projects)
                return True
        return False
