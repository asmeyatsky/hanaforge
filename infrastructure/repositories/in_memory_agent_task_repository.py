"""InMemoryAgentTaskRepository — dev-mode in-memory implementation of AgentTaskRepositoryPort."""

from __future__ import annotations

from datetime import datetime

from domain.entities.agent_task import AgentTask
from domain.value_objects.agent_types import AgentResult, AgentStatus, AgentStep


class InMemoryAgentTaskRepository:
    """Implements AgentTaskRepositoryPort using a plain Python dict."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(task: AgentTask) -> dict:
        return {
            "id": task.id,
            "programme_id": task.programme_id,
            "objective": task.objective,
            "context": task.context,
            "status": task.status.value,
            "steps_taken": [
                {
                    "thought": s.thought,
                    "tool_name": s.tool_name,
                    "tool_input": s.tool_input,
                    "tool_output": s.tool_output,
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in task.steps_taken
            ],
            "max_steps": task.max_steps,
            "result": (
                {
                    "success": task.result.success,
                    "output": task.result.output,
                    "steps_count": len(task.result.steps),
                    "tokens_used": task.result.tokens_used,
                }
                if task.result
                else None
            ),
            "error": task.error,
            "created_at": task.created_at.isoformat(),
        }

    @staticmethod
    def _from_dict(data: dict) -> AgentTask:
        steps = tuple(
            AgentStep(
                thought=s["thought"],
                tool_name=s["tool_name"],
                tool_input=s["tool_input"],
                tool_output=s["tool_output"],
                timestamp=datetime.fromisoformat(s["timestamp"]),
            )
            for s in data["steps_taken"]
        )

        result = None
        if data["result"] is not None:
            result = AgentResult(
                success=data["result"]["success"],
                output=data["result"]["output"],
                steps=steps,  # Re-use the steps from the task
                tokens_used=data["result"]["tokens_used"],
            )

        return AgentTask(
            id=data["id"],
            programme_id=data["programme_id"],
            objective=data["objective"],
            context=data["context"],
            status=AgentStatus(data["status"]),
            steps_taken=steps,
            max_steps=data["max_steps"],
            result=result,
            error=data["error"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    async def save(self, task: AgentTask) -> None:
        self._store[task.id] = self._to_dict(task)

    async def get_by_id(self, id: str) -> AgentTask | None:
        data = self._store.get(id)
        if data is None:
            return None
        return self._from_dict(data)

    async def list_by_programme(self, programme_id: str) -> list[AgentTask]:
        return [
            self._from_dict(data)
            for data in self._store.values()
            if data["programme_id"] == programme_id
        ]

    async def list_recent(self, limit: int = 20) -> list[AgentTask]:
        sorted_items = sorted(
            self._store.values(),
            key=lambda d: d["created_at"],
            reverse=True,
        )
        return [self._from_dict(data) for data in sorted_items[:limit]]
