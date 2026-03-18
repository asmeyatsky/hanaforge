"""Generic DAG orchestrator — executes workflow steps respecting dependency order.

Follows skill2026 Rule 7: parallelize independent steps with asyncio.gather,
validate no cycles before execution.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


@dataclass
class WorkflowStep:
    """A single step in a workflow DAG."""

    name: str
    execute: Callable[..., Awaitable[Any]]
    depends_on: list[str] = field(default_factory=list)


class CycleDetectedError(Exception):
    """Raised when the DAG contains a cycle."""


class DAGOrchestrator:
    """Executes WorkflowSteps respecting dependency order, parallelizing independent steps."""

    def __init__(self, steps: list[WorkflowStep]) -> None:
        self._steps_by_name: dict[str, WorkflowStep] = {s.name: s for s in steps}
        self._validate_no_cycles()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_no_cycles(self) -> None:
        """Kahn's algorithm — topological sort to detect cycles."""
        in_degree: dict[str, int] = {name: 0 for name in self._steps_by_name}
        adjacency: dict[str, list[str]] = defaultdict(list)

        for name, step in self._steps_by_name.items():
            for dep in step.depends_on:
                if dep not in self._steps_by_name:
                    raise ValueError(f"Step '{name}' depends on unknown step '{dep}'")
                adjacency[dep].append(name)
                in_degree[name] += 1

        queue: deque[str] = deque(name for name, degree in in_degree.items() if degree == 0)
        visited = 0

        while queue:
            current = queue.popleft()
            visited += 1
            for neighbour in adjacency[current]:
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    queue.append(neighbour)

        if visited != len(self._steps_by_name):
            raise CycleDetectedError("Workflow DAG contains a cycle — execution order cannot be determined")

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute all steps, returning a dict mapping step name -> result.

        *context* is passed as keyword arguments to each step's execute callable.
        Steps that share no dependency edges run concurrently.
        """
        if context is None:
            context = {}

        results: dict[str, Any] = {}
        completed: set[str] = set()

        # Build dependency mapping for quick lookup
        dependants: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {name: 0 for name in self._steps_by_name}

        for name, step in self._steps_by_name.items():
            for dep in step.depends_on:
                dependants[dep].append(name)
                in_degree[name] += 1

        # Start with root steps (no dependencies)
        ready: set[str] = {name for name, degree in in_degree.items() if degree == 0}

        while ready:
            # Launch all ready steps in parallel
            async def _run_step(step_name: str) -> tuple[str, Any]:
                step = self._steps_by_name[step_name]
                result = await step.execute(results=results, context=context)
                return step_name, result

            batch_results = await asyncio.gather(*[_run_step(name) for name in ready])

            next_ready: set[str] = set()
            for step_name, result in batch_results:
                results[step_name] = result
                completed.add(step_name)

                # Decrement in-degree for dependants; enqueue newly ready steps
                for dependant in dependants[step_name]:
                    in_degree[dependant] -= 1
                    if in_degree[dependant] == 0:
                        next_ready.add(dependant)

            ready = next_ready

        return results
