import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class DiscoveryEngine:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path(__file__).resolve().parent / "discovery_sources"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.discover_file = self.data_dir / "discover_projects.json"

    def run(self, region: str = "Arizona", market: str = "Data Centers") -> List[Dict[str, Any]]:
        projects = [
            {
                "project_name": "West Valley Data Center",
                "city": "Phoenix",
                "state": region,
                "developer": "Northstar Digital Group",
                "market": market,
                "estimated_stage": "Early Planning",
                "estimated_opportunity_score": 84,
                "date_discovered": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "source": "simulated",
                "imported": False,
            },
            {
                "project_name": "Arizona Digital Campus",
                "city": "Phoenix",
                "state": region,
                "developer": "Northstar Digital Group",
                "market": market,
                "estimated_stage": "Early Planning",
                "estimated_opportunity_score": 84,
                "date_discovered": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "source": "simulated",
                "imported": False,
            },
            {
                "project_name": "Mesa Cloud Expansion",
                "city": "Mesa",
                "state": region,
                "developer": "Atlas Infrastructure",
                "market": market,
                "estimated_stage": "Site Control",
                "estimated_opportunity_score": 79,
                "date_discovered": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "source": "simulated",
                "imported": False,
            },
            {
                "project_name": "Tucson AI Hub",
                "city": "Tucson",
                "state": region,
                "developer": "Cobalt Build Partners",
                "market": market,
                "estimated_stage": "Design Development",
                "estimated_opportunity_score": 73,
                "date_discovered": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "source": "simulated",
                "imported": False,
            },
            {
                "project_name": "Flagstaff Compute Facility",
                "city": "Flagstaff",
                "state": region,
                "developer": "Summit Power Ventures",
                "market": market,
                "estimated_stage": "Feasibility",
                "estimated_opportunity_score": 67,
                "date_discovered": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "source": "simulated",
                "imported": False,
            },
            {
                "project_name": "Scottsdale Edge Campus",
                "city": "Scottsdale",
                "state": region,
                "developer": "Silverline Development",
                "market": market,
                "estimated_stage": "Permitting",
                "estimated_opportunity_score": 71,
                "date_discovered": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "source": "simulated",
                "imported": False,
            },
        ]

        self.save(projects)
        return projects

    def load(self) -> List[Dict[str, Any]]:
        if not self.discover_file.exists() or self.discover_file.stat().st_size == 0:
            return self.run()
        with self.discover_file.open(encoding="utf-8") as handle:
            projects = json.load(handle)
        if not projects:
            return self.run()
        if not any(project.get("project_name") in {"West Valley Data Center", "Arizona Digital Campus"} for project in projects):
            return self.run()
        return projects

    def save(self, projects: List[Dict[str, Any]]) -> None:
        with self.discover_file.open("w", encoding="utf-8") as handle:
            json.dump(projects, handle, indent=2)

    def mark_imported(self, project_name: str) -> bool:
        projects = self.load()
        for project in projects:
            if project.get("project_name") == project_name:
                project["imported"] = True
                self.save(projects)
                return True
        return False
