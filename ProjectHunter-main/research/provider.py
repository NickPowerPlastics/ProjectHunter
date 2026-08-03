from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ResearchProvider(ABC):
    name: str = ""

    @abstractmethod
    def research(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        raise NotImplementedError
