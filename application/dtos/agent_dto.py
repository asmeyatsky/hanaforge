"""Agent framework DTOs — Pydantic models for API serialization."""

from __future__ import annotations

from pydantic import BaseModel, Field

from domain.entities.agent_task import AgentTask

# ------------------------------------------------------------------
# Request DTOs
# ------------------------------------------------------------------


class CreateAgentTaskRequest(BaseModel):
    """Request payload to create and start an agent task."""

    programme_id: str
    objective: str
    context: dict = Field(default_factory=dict)
    max_steps: int = Field(default=20, ge=1, le=50)


# ------------------------------------------------------------------
# Response DTOs
# ------------------------------------------------------------------


class AgentStepResponse(BaseModel):
    """Serialisable representation of an agent execution step."""

    thought: str
    tool_name: str | None = None
    tool_input: dict | None = None
    tool_output: str | None = None
    timestamp: str


class AgentResultResponse(BaseModel):
    """Serialisable representation of an agent result."""

    success: bool
    output: str
    steps_count: int
    tokens_used: int


class AgentTaskResponse(BaseModel):
    """Serialisable representation of an AgentTask entity."""

    id: str
    programme_id: str
    objective: str
    context: dict
    status: str
    steps_count: int
    max_steps: int
    result: AgentResultResponse | None = None
    error: str | None = None
    created_at: str
    steps: list[AgentStepResponse] = []

    @staticmethod
    def from_entity(task: AgentTask, include_steps: bool = False) -> AgentTaskResponse:
        result_resp = None
        if task.result is not None:
            result_resp = AgentResultResponse(
                success=task.result.success,
                output=task.result.output,
                steps_count=len(task.result.steps),
                tokens_used=task.result.tokens_used,
            )

        steps_resp = []
        if include_steps:
            steps_resp = [
                AgentStepResponse(
                    thought=s.thought,
                    tool_name=s.tool_name,
                    tool_input=s.tool_input,
                    tool_output=s.tool_output,
                    timestamp=s.timestamp.isoformat(),
                )
                for s in task.steps_taken
            ]

        return AgentTaskResponse(
            id=task.id,
            programme_id=task.programme_id,
            objective=task.objective,
            context=task.context,
            status=task.status.value,
            steps_count=len(task.steps_taken),
            max_steps=task.max_steps,
            result=result_resp,
            error=task.error,
            created_at=task.created_at.isoformat(),
            steps=steps_resp,
        )


class AgentTaskListResponse(BaseModel):
    """Paginated list of agent tasks."""

    tasks: list[AgentTaskResponse]
    total: int
