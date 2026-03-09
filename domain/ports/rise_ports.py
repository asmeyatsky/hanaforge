"""RISE with SAP ports — async boundaries for SAP RISE integration."""

from __future__ import annotations

from typing import Protocol

from domain.value_objects.rise_types import (
    ReadinessCheckResult,
    RISEConnection,
    SAPSystemInfo,
    TransportRequest,
    TransportResult,
)


class RISEConnectorPort(Protocol):
    """Port for interacting with RISE with SAP managed systems.

    Implementations may use RFC (pyrfc) or OData (REST) depending on
    the connection mode specified in the RISEConnection value object.
    """

    async def get_system_info(self, connection: RISEConnection) -> SAPSystemInfo: ...

    async def get_transport_list(self, connection: RISEConnection) -> list[TransportRequest]: ...

    async def execute_transport(self, connection: RISEConnection, transport_id: str) -> TransportResult: ...

    async def get_readiness_check(self, connection: RISEConnection) -> ReadinessCheckResult: ...
