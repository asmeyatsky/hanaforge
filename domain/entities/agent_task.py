"""AgentTask entity — represents an autonomous AI agent execution."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from domain.value_objects.agent_types import AgentResult, AgentStatus, AgentStep


@dataclass(frozen=True)
class AgentTask:
    """An autonomous agent task within a migration programme.

    Frozen dataclass — all mutations return a new instance.
    """

    id: str
    programme_id: str
    objective: str
    context: dict
    status: AgentStatus
    steps_taken: tuple[AgentStep, ...]
    max_steps: int
    result: AgentResult | None
    error: str | None
    created_at: datetime

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def start(self) -> AgentTask:
        """Transition to RUNNING status."""
        if self.status != AgentStatus.PENDING:
            raise ValueError(
                f"Cannot start agent task in status {self.status.value}"
            )
        return replace(self, status=AgentStatus.RUNNING)

    def record_step(self, step: AgentStep) -> AgentTask:
        """Append a step to the execution trace."""
        if self.status != AgentStatus.RUNNING:
            raise ValueError(
                f"Cannot record step for task in status {self.status.value}"
            )
        return replace(self, steps_taken=(*self.steps_taken, step))

    def complete(self, result: AgentResult) -> AgentTask:
        """Mark the task as successfully completed with a result."""
        if self.status != AgentStatus.RUNNING:
            raise ValueError(
                f"Cannot complete task in status {self.status.value}"
            )
        return replace(
            self,
            status=AgentStatus.COMPLETED,
            result=result,
        )

    def fail(self, error_message: str) -> AgentTask:
        """Mark the task as failed with an error description."""
        if self.status != AgentStatus.RUNNING:
            raise ValueError(
                f"Cannot fail task in status {self.status.value}"
            )
        return replace(
            self,
            status=AgentStatus.FAILED,
            error=error_message,
        )

    def cancel(self) -> AgentTask:
        """Cancel the task if it is pending or running."""
        if self.status not in (AgentStatus.PENDING, AgentStatus.RUNNING):
            raise ValueError(
                f"Cannot cancel task in status {self.status.value}"
            )
        return replace(self, status=AgentStatus.CANCELLED)
