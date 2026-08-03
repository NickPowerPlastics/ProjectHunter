import json
from pathlib import Path
from typing import List

from .models import Project


class DiscoverySource:
    def __init__(self, data_dir: Path | None = None):
        base_dir = data_dir or Path(__file__).resolve().parent.parent / "data"
        base_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = base_dir
        self.data_file = self.data_dir / "discover_projects.json"

    def load(self) -> List[Project]:
        if not self.data_file.exists() or self.data_file.stat().st_size == 0:
            return []
        with self.data_file.open(encoding="utf-8") as handle:
            raw_projects = json.load(handle)
        return [Project.from_dict(project) for project in raw_projects]

    def save(self, projects: List[Project]) -> None:
        payload = [project.to_dict() for project in projects]
        with self.data_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
