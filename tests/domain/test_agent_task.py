"""Tests for the AgentTask entity, agent value objects, and tool registry."""

from datetime import datetime, timezone

import pytest

from domain.entities.agent_task import AgentTask
from domain.services.agent_tool_registry import AgentToolRegistry
from domain.value_objects.agent_types import (
    AgentResult,
    AgentStatus,
    AgentStep,
    AgentTool,
)

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

_NOW = datetime(2026, 3, 9, 12, 0, 0, tzinfo=timezone.utc)


def _make_step(
    *,
    thought: str = "Thinking...",
    tool_name: str | None = "check_programme_status",
    tool_input: dict | None = None,
    tool_output: str | None = '{"status": "CREATED"}',
) -> AgentStep:
    return AgentStep(
        thought=thought,
        tool_name=tool_name,
        tool_input=tool_input or {"programme_id": "prog-001"},
        tool_output=tool_output,
        timestamp=_NOW,
    )


def _make_result(*, success: bool = True, steps: int = 2) -> AgentResult:
    return AgentResult(
        success=success,
        output="Migration readiness summary.",
        steps=tuple(_make_step() for _ in range(steps)),
        tokens_used=1500,
    )


def _make_task(
    *,
    status: AgentStatus = AgentStatus.PENDING,
    steps: tuple[AgentStep, ...] = (),
    result: AgentResult | None = None,
    error: str | None = None,
) -> AgentTask:
    return AgentTask(
        id="task-001",
        programme_id="prog-001",
        objective="Check migration readiness",
        context={"landscape_id": "ls-001"},
        status=status,
        steps_taken=steps,
        max_steps=20,
        result=result,
        error=error,
        created_at=_NOW,
    )


# ------------------------------------------------------------------
# AgentStatus enum
# ------------------------------------------------------------------


class TestAgentStatus:
    def test_all_statuses_defined(self) -> None:
        assert set(s.value for s in AgentStatus) == {
            "PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED",
        }

    def test_enum_round_trip(self) -> None:
        for s in AgentStatus:
            assert AgentStatus(s.value) == s


# ------------------------------------------------------------------
# AgentStep frozen dataclass
# ------------------------------------------------------------------


class TestAgentStep:
    def test_step_creation(self) -> None:
        step = _make_step()
        assert step.thought == "Thinking..."
        assert step.tool_name == "check_programme_status"
        assert step.tool_input == {"programme_id": "prog-001"}
        assert step.tool_output == '{"status": "CREATED"}'
        assert step.timestamp == _NOW

    def test_step_is_frozen(self) -> None:
        step = _make_step()
        with pytest.raises(AttributeError):
            step.thought = "new thought"  # type: ignore[misc]

    def test_step_without_tool(self) -> None:
        step = AgentStep(
            thought="Final summary.",
            tool_name=None,
            tool_input=None,
            tool_output=None,
            timestamp=_NOW,
        )
        assert step.tool_name is None
        assert step.tool_input is None


# ------------------------------------------------------------------
# AgentResult frozen dataclass
# ------------------------------------------------------------------


class TestAgentResult:
    def test_result_creation(self) -> None:
        result = _make_result()
        assert result.success is True
        assert result.output == "Migration readiness summary."
        assert len(result.steps) == 2
        assert result.tokens_used == 1500

    def test_result_is_frozen(self) -> None:
        result = _make_result()
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]

    def test_failed_result(self) -> None:
        result = AgentResult(
            success=False,
            output="Agent reached maximum steps.",
            steps=(),
            tokens_used=3000,
        )
        assert result.success is False
        assert result.tokens_used == 3000


# ------------------------------------------------------------------
# AgentTool frozen dataclass
# ------------------------------------------------------------------


class TestAgentTool:
    def test_tool_creation(self) -> None:
        tool = AgentTool(
            name="check_programme_status",
            description="Reads programme details.",
            input_schema={
                "type": "object",
                "properties": {
                    "programme_id": {"type": "string"},
                },
                "required": ["programme_id"],
            },
        )
        assert tool.name == "check_programme_status"
        assert "programme_id" in tool.input_schema["properties"]

    def test_tool_is_frozen(self) -> None:
        tool = AgentTool(name="t", description="d", input_schema={})
        with pytest.raises(AttributeError):
            tool.name = "new"  # type: ignore[misc]


# ------------------------------------------------------------------
# AgentTask entity — creation
# ------------------------------------------------------------------


class TestAgentTaskCreation:
    def test_create_task_with_valid_data(self) -> None:
        task = _make_task()

        assert task.id == "task-001"
        assert task.programme_id == "prog-001"
        assert task.objective == "Check migration readiness"
        assert task.context == {"landscape_id": "ls-001"}
        assert task.status == AgentStatus.PENDING
        assert task.steps_taken == ()
        assert task.max_steps == 20
        assert task.result is None
        assert task.error is None
        assert task.created_at == _NOW


# ------------------------------------------------------------------
# AgentTask entity — start
# ------------------------------------------------------------------


class TestAgentTaskStart:
    def test_start_from_pending(self) -> None:
        task = _make_task()
        started = task.start()
        assert started.status == AgentStatus.RUNNING

    def test_cannot_start_from_running(self) -> None:
        task = _make_task(status=AgentStatus.RUNNING)
        with pytest.raises(ValueError, match="Cannot start"):
            task.start()

    def test_cannot_start_from_completed(self) -> None:
        task = _make_task(status=AgentStatus.COMPLETED)
        with pytest.raises(ValueError, match="Cannot start"):
            task.start()


# ------------------------------------------------------------------
# AgentTask entity — record_step
# ------------------------------------------------------------------


class TestAgentTaskRecordStep:
    def test_record_step_appends(self) -> None:
        task = _make_task(status=AgentStatus.RUNNING)
        step = _make_step()
        updated = task.record_step(step)

        assert len(updated.steps_taken) == 1
        assert updated.steps_taken[0] == step

    def test_record_multiple_steps(self) -> None:
        task = _make_task(status=AgentStatus.RUNNING)
        step1 = _make_step(thought="Step 1")
        step2 = _make_step(thought="Step 2")

        updated = task.record_step(step1).record_step(step2)
        assert len(updated.steps_taken) == 2
        assert updated.steps_taken[0].thought == "Step 1"
        assert updated.steps_taken[1].thought == "Step 2"

    def test_cannot_record_step_if_not_running(self) -> None:
        task = _make_task(status=AgentStatus.PENDING)
        with pytest.raises(ValueError, match="Cannot record step"):
            task.record_step(_make_step())


# ------------------------------------------------------------------
# AgentTask entity — complete
# ------------------------------------------------------------------


class TestAgentTaskComplete:
    def test_complete_from_running(self) -> None:
        task = _make_task(status=AgentStatus.RUNNING)
        result = _make_result()
        completed = task.complete(result)

        assert completed.status == AgentStatus.COMPLETED
        assert completed.result is not None
        assert completed.result.success is True

    def test_cannot_complete_from_pending(self) -> None:
        task = _make_task(status=AgentStatus.PENDING)
        with pytest.raises(ValueError, match="Cannot complete"):
            task.complete(_make_result())


# ------------------------------------------------------------------
# AgentTask entity — fail
# ------------------------------------------------------------------


class TestAgentTaskFail:
    def test_fail_from_running(self) -> None:
        task = _make_task(status=AgentStatus.RUNNING)
        failed = task.fail("Something went wrong")

        assert failed.status == AgentStatus.FAILED
        assert failed.error == "Something went wrong"

    def test_cannot_fail_from_completed(self) -> None:
        task = _make_task(status=AgentStatus.COMPLETED)
        with pytest.raises(ValueError, match="Cannot fail"):
            task.fail("error")


# ------------------------------------------------------------------
# AgentTask entity — cancel
# ------------------------------------------------------------------


class TestAgentTaskCancel:
    def test_cancel_from_pending(self) -> None:
        task = _make_task(status=AgentStatus.PENDING)
        cancelled = task.cancel()
        assert cancelled.status == AgentStatus.CANCELLED

    def test_cancel_from_running(self) -> None:
        task = _make_task(status=AgentStatus.RUNNING)
        cancelled = task.cancel()
        assert cancelled.status == AgentStatus.CANCELLED

    def test_cannot_cancel_from_completed(self) -> None:
        task = _make_task(status=AgentStatus.COMPLETED)
        with pytest.raises(ValueError, match="Cannot cancel"):
            task.cancel()

    def test_cannot_cancel_from_failed(self) -> None:
        task = _make_task(status=AgentStatus.FAILED)
        with pytest.raises(ValueError, match="Cannot cancel"):
            task.cancel()


# ------------------------------------------------------------------
# AgentTask entity — immutability
# ------------------------------------------------------------------


class TestAgentTaskImmutability:
    def test_task_is_frozen(self) -> None:
        task = _make_task()
        with pytest.raises(AttributeError):
            task.status = AgentStatus.RUNNING  # type: ignore[misc]

    def test_start_does_not_mutate_original(self) -> None:
        original = _make_task()
        started = original.start()

        assert original.status == AgentStatus.PENDING
        assert started.status == AgentStatus.RUNNING

    def test_record_step_does_not_mutate_original(self) -> None:
        original = _make_task(status=AgentStatus.RUNNING)
        updated = original.record_step(_make_step())

        assert len(original.steps_taken) == 0
        assert len(updated.steps_taken) == 1


# ------------------------------------------------------------------
# AgentToolRegistry
# ------------------------------------------------------------------


class _StubTool:
    """Minimal implementation of AgentToolPort for testing."""

    def __init__(self, name: str, description: str = "A test tool") -> None:
        self.name = name
        self.description = description
        self.input_schema: dict = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        }

    async def execute(self, params: dict) -> dict:
        return {"ok": True, "params": params}


class TestAgentToolRegistry:
    def test_register_and_get(self) -> None:
        registry = AgentToolRegistry()
        tool = _StubTool("my_tool")
        registry.register(tool)

        assert registry.get("my_tool") is tool

    def test_get_returns_none_for_unknown(self) -> None:
        registry = AgentToolRegistry()
        assert registry.get("nonexistent") is None

    def test_get_or_raise_raises_for_unknown(self) -> None:
        registry = AgentToolRegistry()
        with pytest.raises(KeyError, match="not registered"):
            registry.get_or_raise("nonexistent")

    def test_list_names(self) -> None:
        registry = AgentToolRegistry()
        registry.register(_StubTool("b_tool"))
        registry.register(_StubTool("a_tool"))

        assert registry.list_names() == ["a_tool", "b_tool"]

    def test_register_many(self) -> None:
        registry = AgentToolRegistry()
        tools = [_StubTool("t1"), _StubTool("t2"), _StubTool("t3")]
        registry.register_many(tools)

        assert registry.list_names() == ["t1", "t2", "t3"]

    def test_get_tool_schemas_all(self) -> None:
        registry = AgentToolRegistry()
        registry.register(_StubTool("tool_a", "Desc A"))
        registry.register(_StubTool("tool_b", "Desc B"))

        schemas = registry.get_tool_schemas()
        assert len(schemas) == 2
        assert all(isinstance(s, AgentTool) for s in schemas)
        names = {s.name for s in schemas}
        assert names == {"tool_a", "tool_b"}

    def test_get_tool_schemas_subset(self) -> None:
        registry = AgentToolRegistry()
        registry.register(_StubTool("tool_a"))
        registry.register(_StubTool("tool_b"))
        registry.register(_StubTool("tool_c"))

        schemas = registry.get_tool_schemas(names=["tool_a", "tool_c"])
        assert len(schemas) == 2
        names = {s.name for s in schemas}
        assert names == {"tool_a", "tool_c"}

    @pytest.mark.asyncio
    async def test_execute_tool(self) -> None:
        registry = AgentToolRegistry()
        registry.register(_StubTool("my_tool"))

        result = await registry.execute("my_tool", {"id": "123"})
        assert result == {"ok": True, "params": {"id": "123"}}

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_raises(self) -> None:
        registry = AgentToolRegistry()
        with pytest.raises(KeyError, match="not registered"):
            await registry.execute("missing", {})

    def test_overwrite_registration_logs_warning(self) -> None:
        registry = AgentToolRegistry()
        registry.register(_StubTool("dup"))
        registry.register(_StubTool("dup"))

        # Still only one entry
        assert registry.list_names() == ["dup"]
