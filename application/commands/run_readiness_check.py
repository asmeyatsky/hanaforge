"""RunReadinessCheckUseCase — executes RISE readiness check against SAP system."""

from __future__ import annotations

from pydantic import BaseModel

from domain.ports.rise_ports import RISEConnectorPort
from domain.ports.repository_ports import ProgrammeRepositoryPort
from domain.value_objects.rise_types import (
    RISEConnection,
    RISEConnectionMode,
    RISESystemType,
)


class ReadinessCheckResponse(BaseModel):
    """API-serialisable readiness check result."""

    programme_id: str
    overall_status: str
    total_checks: int
    passed: int
    warnings: int
    failed: int
    checks: list[dict]


class RunReadinessCheckUseCase:
    """Single-responsibility use case: run RISE readiness check for a programme."""

    def __init__(
        self,
        programme_repo: ProgrammeRepositoryPort,
        rise_connector: RISEConnectorPort,
    ) -> None:
        self._programme_repo = programme_repo
        self._rise_connector = rise_connector

    async def execute(
        self,
        programme_id: str,
        host: str,
        port: int = 443,
        client: str = "100",
        user: str = "",
        system_type: str = "S4HANA_ON_PREMISE",
        mode: str = "ODATA",
    ) -> ReadinessCheckResponse:
        # 1. Validate programme exists
        programme = await self._programme_repo.get_by_id(programme_id)
        if programme is None:
            raise ValueError(f"Programme {programme_id} not found")

        # 2. Build connection object
        connection = RISEConnection(
            host=host,
            port=port,
            client=client,
            user=user,
            system_type=RISESystemType(system_type),
            mode=RISEConnectionMode(mode),
        )

        # 3. Execute readiness check via RISE connector
        result = await self._rise_connector.get_readiness_check(connection)

        # 4. Build response
        checks_list = [
            {
                "name": check.name,
                "status": check.status.value,
                "message": check.message,
                "severity": check.severity.value,
            }
            for check in result.checks
        ]

        return ReadinessCheckResponse(
            programme_id=programme_id,
            overall_status=result.overall_status.value,
            total_checks=len(result.checks),
            passed=result.passed_count,
            warnings=result.warning_count,
            failed=result.failed_count,
            checks=checks_list,
        )
