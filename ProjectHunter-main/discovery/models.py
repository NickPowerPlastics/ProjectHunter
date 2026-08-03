from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class Project:
    id: Optional[int] = None
    project_name: str = ""
    city: str = ""
    state: str = ""
    market: str = ""
    developer: str = ""
    general_contractor: str = ""
    electrical_contractor: str = ""
    business_line: str = ""
    stage: str = ""
    status: str = ""
    next_action: str = ""
    opportunity_score: int = 0
    source: str = ""
    date_discovered: str = ""
    imported: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        return cls(
            id=data.get("id"),
            project_name=data.get("project_name", data.get("name", "")),
            city=data.get("city", ""),
            state=data.get("state", ""),
            market=data.get("market", ""),
            developer=data.get("developer", ""),
            general_contractor=data.get("general_contractor", ""),
            electrical_contractor=data.get("electrical_contractor", ""),
            business_line=data.get("business_line", ""),
            stage=data.get("stage", data.get("estimated_stage", "")),
            status=data.get("status", ""),
            next_action=data.get("next_action", ""),
            opportunity_score=data.get("opportunity_score", data.get("estimated_opportunity_score", 0)),
            source=data.get("source", ""),
            date_discovered=data.get("date_discovered", ""),
            imported=data.get("imported", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
