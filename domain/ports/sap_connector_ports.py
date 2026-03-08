"""SAP connector ports — boundaries for live SAP system integration."""

from __future__ import annotations

from typing import Any, Protocol


class SAPConnectionPort(Protocol):
    async def connect(
        self,
        host: str,
        system_number: str,
        client: str,
        user: str,
        password: str,
    ) -> bool: ...

    async def disconnect(self) -> None: ...


class SAPDiscoveryPort(Protocol):
    async def extract_custom_objects(self, connection: Any) -> list[dict]: ...
    async def extract_integration_points(self, connection: Any) -> list[dict]: ...
    async def extract_landscape_metadata(self, connection: Any) -> dict: ...
