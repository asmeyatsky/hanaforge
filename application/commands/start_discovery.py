"""StartDiscoveryUseCase — connects to SAP and discovers landscape metadata."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from application.dtos.analysis_dto import DiscoveryResultsResponse
from domain.entities.sap_landscape import SAPLandscape
from domain.events.programme_events import DiscoveryStartedEvent
from domain.ports import (
    EventBusPort,
    LandscapeRepositoryPort,
    ProgrammeRepositoryPort,
    SAPDiscoveryPort,
)
from domain.value_objects.object_type import SystemRole


class StartDiscoveryUseCase:
    """Single-responsibility use case: initiate SAP landscape discovery."""

    def __init__(
        self,
        programme_repo: ProgrammeRepositoryPort,
        landscape_repo: LandscapeRepositoryPort,
        sap_discovery: SAPDiscoveryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._programme_repo = programme_repo
        self._landscape_repo = landscape_repo
        self._sap_discovery = sap_discovery
        self._event_bus = event_bus

    async def execute(
        self,
        programme_id: str,
        connection_params: dict,
    ) -> DiscoveryResultsResponse:
        # 1. Load programme and transition to discovery state
        programme = await self._programme_repo.get_by_id(programme_id)
        if programme is None:
            raise ValueError(f"Programme {programme_id} not found")

        programme = programme.start_discovery()
        await self._programme_repo.save(programme)

        # 2. Connect to SAP and extract metadata
        discovery_result = await self._sap_discovery.discover(connection_params)

        # 3. Build SAPLandscape entity from discovery output
        landscape_id = str(uuid.uuid4())
        system_id = discovery_result.get("system_id", "UNKNOWN")
        db_size_gb = discovery_result.get("db_size_gb", 0.0)
        custom_objects = discovery_result.get("custom_objects", [])
        integration_points = discovery_result.get("integration_points", [])
        system_role_raw = discovery_result.get("system_role", "DEV")

        landscape = SAPLandscape(
            id=landscape_id,
            programme_id=programme_id,
            system_id=system_id,
            system_role=SystemRole(system_role_raw),
            db_size_gb=db_size_gb,
            number_of_users=discovery_result.get("number_of_users", 0),
            custom_object_count=len(custom_objects),
            integration_points=tuple(
                ip.get("name", str(ip)) if isinstance(ip, dict) else str(ip) for ip in integration_points
            ),
            created_at=datetime.now(timezone.utc),
        )
        await self._landscape_repo.save(landscape)

        # 4. Publish discovery started event
        event = DiscoveryStartedEvent(
            aggregate_id=programme_id,
            landscape_id=landscape_id,
        )
        await self._event_bus.publish(event)

        # 5. Build complexity and recommendation data if available
        complexity_dict: dict | None = None
        if discovery_result.get("complexity_score") is not None:
            cs = discovery_result["complexity_score"]
            complexity_dict = {
                "score": cs.get("score"),
                "risk_level": cs.get("risk_level"),
                "benchmark_percentile": cs.get("benchmark_percentile"),
            }

        recommendation_dict: dict | None = None
        if discovery_result.get("migration_recommendation") is not None:
            rec = discovery_result["migration_recommendation"]
            recommendation_dict = {
                "approach": rec.get("approach"),
                "confidence": rec.get("confidence"),
                "reasoning": rec.get("reasoning"),
            }

        return DiscoveryResultsResponse(
            programme_id=programme_id,
            landscape_id=landscape_id,
            system_id=system_id,
            custom_object_count=len(custom_objects),
            integration_point_count=len(integration_points),
            complexity_score=complexity_dict,
            migration_recommendation=recommendation_dict,
        )
