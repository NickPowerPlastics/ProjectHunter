from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from .models import Project
from .provider import DiscoveryProvider


class MockProvider(DiscoveryProvider):
    name = "mock"

    def discover(self, region: str, market: str) -> List[Project]:
        return [
            Project(
                project_name="West Valley Data Center",
                city="Phoenix",
                state=region,
                market=market,
                developer="Northstar Digital Group",
                general_contractor="",
                electrical_contractor="",
                business_line="Duct Bank",
                stage="Early Planning",
                status="New",
                next_action="Follow up with developer",
                opportunity_score=84,
                source=self.name,
                date_discovered=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                imported=False,
            ),
            Project(
                project_name="Arizona Digital Campus",
                city="Phoenix",
                state=region,
                market=market,
                developer="Atlas Infrastructure",
                general_contractor="",
                electrical_contractor="",
                business_line="Duct Bank",
                stage="Site Control",
                status="New",
                next_action="Schedule site visit",
                opportunity_score=79,
                source=self.name,
                date_discovered=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                imported=False,
            ),
            Project(
                project_name="Tucson AI Hub",
                city="Tucson",
                state=region,
                market=market,
                developer="Cobalt Build Partners",
                general_contractor="",
                electrical_contractor="",
                business_line="Duct Bank",
                stage="Design Development",
                status="New",
                next_action="Prepare proposal",
                opportunity_score=73,
                source=self.name,
                date_discovered=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                imported=False,
            ),
            Project(
                project_name="Flagstaff Compute Facility",
                city="Flagstaff",
                state=region,
                market=market,
                developer="Summit Power Ventures",
                general_contractor="",
                electrical_contractor="",
                business_line="Duct Bank",
                stage="Feasibility",
                status="New",
                next_action="Confirm scope",
                opportunity_score=67,
                source=self.name,
                date_discovered=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                imported=False,
            ),
            Project(
                project_name="Scottsdale Edge Campus",
                city="Scottsdale",
                state=region,
                market=market,
                developer="Silverline Development",
                general_contractor="",
                electrical_contractor="",
                business_line="Duct Bank",
                stage="Permitting",
                status="New",
                next_action="Secure approvals",
                opportunity_score=71,
                source=self.name,
                date_discovered=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                imported=False,
            ),
        ]


class DataCenterDynamicsProvider(DiscoveryProvider):
    name = "datacenterdynamics"

    def discover(self, region: str, market: str) -> List[Project]:
        return []
