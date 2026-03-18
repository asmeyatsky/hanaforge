"""Cutover Commander ports — Protocol-based boundaries for infrastructure adapters."""

from __future__ import annotations

from typing import Protocol

from domain.entities.cutover_execution import CutoverExecution
from domain.entities.cutover_runbook import CutoverRunbook
from domain.entities.hypercare_session import HypercareSession


class RunbookRepositoryPort(Protocol):
    """Persistence boundary for CutoverRunbook aggregates."""

    async def save(self, runbook: CutoverRunbook) -> None: ...
    async def get_by_id(self, id: str) -> CutoverRunbook | None: ...
    async def get_latest_by_programme(self, programme_id: str) -> CutoverRunbook | None: ...
    async def list_by_programme(self, programme_id: str) -> list[CutoverRunbook]: ...


class CutoverExecutionRepositoryPort(Protocol):
    """Persistence boundary for CutoverExecution aggregates."""

    async def save(self, execution: CutoverExecution) -> None: ...
    async def get_by_id(self, id: str) -> CutoverExecution | None: ...
    async def get_active(self, programme_id: str) -> CutoverExecution | None: ...


class HypercareRepositoryPort(Protocol):
    """Persistence boundary for HypercareSession aggregates."""

    async def save(self, session: HypercareSession) -> None: ...
    async def get_by_id(self, id: str) -> HypercareSession | None: ...
    async def get_active(self, programme_id: str) -> HypercareSession | None: ...


class SystemHealthCheckPort(Protocol):
    """Adapter boundary for live system health checks."""

    async def check_hana_availability(self, connection_params: dict) -> dict: ...
    async def check_interface_connectivity(self, endpoints: list[dict]) -> dict: ...
    async def check_performance_baseline(self, connection_params: dict) -> dict: ...


class RunbookAIGeneratorPort(Protocol):
    """Adapter boundary for AI-powered runbook generation."""

    async def generate_runbook(self, programme_artefacts: dict) -> dict: ...


class NotificationPort(Protocol):
    """Adapter boundary for alert and notification delivery."""

    async def send_alert(self, channels: list[str], message: str, severity: str) -> bool: ...


class TicketingPort(Protocol):
    """Adapter boundary for support ticket system integration."""

    async def create_ticket(self, title: str, description: str, severity: str, component: str) -> str: ...

    async def update_ticket(self, ticket_id: str, status: str, resolution: str) -> bool: ...
