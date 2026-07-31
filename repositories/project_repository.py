import json
from pathlib import Path
from typing import Any, List


def calculate_score(project: dict[str, Any]) -> int:
    score = 0
    market = (project.get("market") or "").lower()
    business_line = (project.get("business_line") or "").lower()
    status = (project.get("status") or "").lower()
    electrical_contractor = (project.get("electrical_contractor") or "").strip()
    general_contractor = (project.get("general_contractor") or "").strip()

    if "data center" in market:
        score += 40
    if electrical_contractor:
        score += 20
    if general_contractor:
        score += 10
    if "need" in status:
        score += 10
    if business_line == "duct bank":
        score += 20

    return min(score, 100)


class ProjectRepository:
    def __init__(self, path: str | Path | None = None):
        root_dir = Path(__file__).resolve().parents[1]
        self.path = Path(path) if path is not None else root_dir / "projects.json"

    def calculate_score(self, project: dict[str, Any]) -> int:
        return calculate_score(project)

    def normalize_projects(self, projects: List[dict[str, Any]]) -> List[dict[str, Any]]:
        normalized = []
        for project in projects:
            normalized_project = dict(project)
            if "score" not in normalized_project or normalized_project.get("score") in (None, ""):
                normalized_project["score"] = self.calculate_score(normalized_project)
            else:
                normalized_project["score"] = int(normalized_project.get("score", 0))
            normalized_project["favorite"] = bool(normalized_project.get("favorite", False))
            normalized.append(normalized_project)
        return normalized

    def load_projects(self) -> List[dict[str, Any]]:
        with self.path.open(encoding="utf-8") as handle:
            return self.normalize_projects(json.load(handle))

    def save_projects(self, projects: List[dict[str, Any]]) -> Path:
        temp_path = self.path.with_suffix(".tmp")

        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(projects, handle, indent=2)

        temp_path.replace(self.path)
        return self.path


project_repository = ProjectRepository()


def load_projects() -> List[dict[str, Any]]:
    return project_repository.load_projects()


def save_projects(projects: List[dict[str, Any]]) -> Path:
    return project_repository.save_projects(projects)
