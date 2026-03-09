"""Agent framework value objects — status, step, result, and tool definitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AgentStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class AgentStep:
    """A single step in an agent's execution trace."""

    thought: str
    tool_name: str | None
    tool_input: dict | None
    tool_output: str | None
    timestamp: datetime


@dataclass(frozen=True)
class AgentResult:
    """Outcome of a completed agent execution loop."""

    success: bool
    output: str
    steps: tuple[AgentStep, ...]
    tokens_used: int


@dataclass(frozen=True)
class AgentTool:
    """Schema descriptor for a tool available to the agent."""

    name: str
    description: str
    input_schema: dict
