"""Agent framework ports — async boundaries for agent execution and tools."""

from __future__ import annotations

from typing import Protocol

from domain.entities.agent_task import AgentTask
from domain.value_objects.agent_types import AgentResult, AgentTool


class AgentExecutorPort(Protocol):
    """Infrastructure boundary for executing an autonomous agent loop."""

    async def execute_agent_loop(
        self,
        task: AgentTask,
        tools: list[AgentTool],
        max_steps: int = 20,
    ) -> AgentResult: ...


class AgentToolPort(Protocol):
    """Contract for a single tool that an agent can invoke."""

    name: str
    description: str

    async def execute(self, params: dict) -> dict: ...


class AgentTaskRepositoryPort(Protocol):
    """Persistence boundary for AgentTask aggregates."""

    async def save(self, task: AgentTask) -> None: ...
    async def get_by_id(self, id: str) -> AgentTask | None: ...
    async def list_by_programme(self, programme_id: str) -> list[AgentTask]: ...
    async def list_recent(self, limit: int = 20) -> list[AgentTask]: ...
