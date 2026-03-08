"""SAP Landscape entity — captures a single system landscape snapshot."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from domain.value_objects.object_type import SystemRole


@dataclass(frozen=True)
class SAPLandscape:
    id: str
    programme_id: str
    system_id: str
    system_role: SystemRole
    db_size_gb: float
    number_of_users: int
    custom_object_count: int
    integration_points: tuple[str, ...]
    created_at: datetime

    def record_custom_objects(self, count: int) -> SAPLandscape:
        if count < 0:
            raise ValueError(f"custom_object_count cannot be negative, got {count}")
        return replace(self, custom_object_count=count)

    def add_integration_point(self, point: str) -> SAPLandscape:
        if not point:
            raise ValueError("integration point must not be empty")
        return replace(self, integration_points=(*self.integration_points, point))
