from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from .models import Project


class DiscoveryProvider(ABC):
    name: str = ""

    @abstractmethod
    def discover(self, region: str, market: str) -> List[Project]:
        raise NotImplementedError
