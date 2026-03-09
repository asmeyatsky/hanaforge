"""RunAgentTaskUseCase — creates and executes an autonomous agent task."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from domain.entities.agent_task import AgentTask
from domain.ports.agent_ports import AgentExecutorPort, AgentTaskRepositoryPort
from domain.services.agent_tool_registry import AgentToolRegistry
from domain.value_objects.agent_types import AgentStatus

logger = logging.getLogger(__name__)

# Tool names relevant to different objective categories
_OBJECTIVE_TOOL_MAP: dict[str, list[str]] = {
    "discovery": [
        "check_programme_status",
        "list_custom_objects",
    ],
    "analysis": [
        "check_programme_status",
        "list_custom_objects",
        "run_analysis",
    ],
    "data_readiness": [
        "check_programme_status",
        "check_data_readiness",
    ],
    "testing": [
        "check_programme_status",
        "list_custom_objects",
        "generate_test_scenarios",
    ],
    "migration": [
        "check_programme_status",
        "check_migration_status",
        "check_data_readiness",
    ],
}


class RunAgentTaskUseCase:
    """Single-responsibility use case: create an agent task and run the agent loop.

    Selects the appropriate tools based on the objective keywords, persists the
    task before and after execution, and captures the full audit trail.
    """

    def __init__(
        self,
        agent_task_repo: AgentTaskRepositoryPort,
        agent_executor: AgentExecutorPort,
        tool_registry: AgentToolRegistry,
    ) -> None:
        self._agent_task_repo = agent_task_repo
        self._agent_executor = agent_executor
        self._tool_registry = tool_registry

    async def execute(
        self,
        programme_id: str,
        objective: str,
        context: dict | None = None,
        max_steps: int = 20,
    ) -> AgentTask:
        """Create and execute an agent task, returning the completed task entity."""

        # 1. Create the task entity
        task = AgentTask(
            id=str(uuid.uuid4()),
            programme_id=programme_id,
            objective=objective,
            context=context or {},
            status=AgentStatus.PENDING,
            steps_taken=(),
            max_steps=max_steps,
            result=None,
            error=None,
            created_at=datetime.now(timezone.utc),
        )

        # Persist the initial task state
        await self._agent_task_repo.save(task)
        logger.info("Created agent task %s for programme %s", task.id, programme_id)

        # 2. Select tools based on objective keywords
        tool_names = self._select_tools(objective)
        tools = self._tool_registry.get_tool_schemas(tool_names if tool_names else None)

        if not tools:
            # No tools available — fail gracefully
            task = task.start()
            task = task.fail("No agent tools are available for execution.")
            await self._agent_task_repo.save(task)
            return task

        # 3. Start the task
        task = task.start()
        await self._agent_task_repo.save(task)

        # 4. Run the agent loop
        try:
            result = await self._agent_executor.execute_agent_loop(
                task=task,
                tools=tools,
                max_steps=max_steps,
            )

            # 5. Complete with result
            # Update steps from the result
            for step in result.steps:
                task = task.record_step(step)
            task = task.complete(result)

            logger.info(
                "Agent task %s completed (success=%s, steps=%d, tokens=%d)",
                task.id, result.success, len(result.steps), result.tokens_used,
            )
        except asyncio.CancelledError:
            task = task.fail("Agent task was cancelled.")
            logger.warning("Agent task %s was cancelled", task.id)
        except Exception as exc:
            task = task.fail(f"Agent execution error: {exc}")
            logger.error("Agent task %s failed: %s", task.id, exc, exc_info=True)

        # 6. Persist the final state
        await self._agent_task_repo.save(task)
        return task

    @staticmethod
    def _select_tools(objective: str) -> list[str] | None:
        """Select tool names based on keywords found in the objective.

        Returns None to indicate "use all available tools" if no keywords match.
        """
        objective_lower = objective.lower()
        matched_tools: set[str] = set()

        for keyword, tools in _OBJECTIVE_TOOL_MAP.items():
            if keyword in objective_lower:
                matched_tools.update(tools)

        if not matched_tools:
            # No specific keyword match — return None to use all tools
            return None

        return sorted(matched_tools)
