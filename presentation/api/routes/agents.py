"""Agent routes — endpoints for creating, monitoring, and cancelling agent tasks."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from application.commands.run_agent_task import RunAgentTaskUseCase
from application.dtos.agent_dto import (
    AgentTaskListResponse,
    AgentTaskResponse,
    CreateAgentTaskRequest,
)
from domain.ports.agent_ports import AgentTaskRepositoryPort
from presentation.api.middleware.auth import get_current_user

router = APIRouter(prefix="", tags=["Agentic Execution"])


# ------------------------------------------------------------------
# Background runner — executes the agent task outside the request
# ------------------------------------------------------------------

async def _run_agent_in_background(
    use_case: RunAgentTaskUseCase,
    programme_id: str,
    objective: str,
    context: dict,
    max_steps: int,
) -> None:
    """Run the agent loop as a background task."""
    await use_case.execute(
        programme_id=programme_id,
        objective=objective,
        context=context,
        max_steps=max_steps,
    )


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.post(
    "/tasks",
    response_model=AgentTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and start an agent task",
)
async def create_agent_task(
    body: CreateAgentTaskRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    _user=Depends(get_current_user),
) -> AgentTaskResponse:
    """Create an autonomous agent task that will execute in the background.

    The task is created immediately and execution begins asynchronously.
    Poll GET /tasks/{id} to monitor progress.
    """
    container = request.app.state.container
    use_case: RunAgentTaskUseCase = container.resolve(RunAgentTaskUseCase)

    # Create the task synchronously so we can return its ID
    agent_task_repo: AgentTaskRepositoryPort = container.resolve("AgentTaskRepositoryPort")

    # We need to create the task inline to get the ID, then start the loop
    # in the background.  The use case handles both creation and execution,
    # so we start the full use case in background.
    import uuid
    from datetime import datetime, timezone
    from domain.entities.agent_task import AgentTask
    from domain.value_objects.agent_types import AgentStatus

    task = AgentTask(
        id=str(uuid.uuid4()),
        programme_id=body.programme_id,
        objective=body.objective,
        context=body.context,
        status=AgentStatus.PENDING,
        steps_taken=(),
        max_steps=body.max_steps,
        result=None,
        error=None,
        created_at=datetime.now(timezone.utc),
    )
    await agent_task_repo.save(task)

    # Schedule the full execution in the background
    background_tasks.add_task(
        _run_agent_in_background,
        use_case=use_case,
        programme_id=body.programme_id,
        objective=body.objective,
        context=body.context,
        max_steps=body.max_steps,
    )

    return AgentTaskResponse.from_entity(task)


@router.get(
    "/tasks/{task_id}",
    response_model=AgentTaskResponse,
    summary="Get agent task status and results",
)
async def get_agent_task(
    task_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> AgentTaskResponse:
    """Retrieve the current status, execution steps, and result of an agent task."""
    container = request.app.state.container
    agent_task_repo: AgentTaskRepositoryPort = container.resolve("AgentTaskRepositoryPort")
    task = await agent_task_repo.get_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent task '{task_id}' not found.",
        )
    return AgentTaskResponse.from_entity(task, include_steps=True)


@router.get(
    "/tasks",
    response_model=AgentTaskListResponse,
    summary="List recent agent tasks",
)
async def list_agent_tasks(
    request: Request,
    programme_id: str | None = None,
    limit: int = 20,
    _user=Depends(get_current_user),
) -> AgentTaskListResponse:
    """List recent agent tasks, optionally filtered by programme."""
    container = request.app.state.container
    agent_task_repo: AgentTaskRepositoryPort = container.resolve("AgentTaskRepositoryPort")

    if programme_id:
        tasks = await agent_task_repo.list_by_programme(programme_id)
    else:
        tasks = await agent_task_repo.list_recent(limit=limit)

    return AgentTaskListResponse(
        tasks=[AgentTaskResponse.from_entity(t) for t in tasks],
        total=len(tasks),
    )


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=AgentTaskResponse,
    summary="Cancel a running agent task",
)
async def cancel_agent_task(
    task_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> AgentTaskResponse:
    """Cancel a pending or running agent task."""
    container = request.app.state.container
    agent_task_repo: AgentTaskRepositoryPort = container.resolve("AgentTaskRepositoryPort")

    task = await agent_task_repo.get_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent task '{task_id}' not found.",
        )

    try:
        task = task.cancel()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await agent_task_repo.save(task)
    return AgentTaskResponse.from_entity(task)
