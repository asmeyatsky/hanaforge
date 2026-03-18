"""Built-in agent tools for SAP migration workflows.

Each tool implements the AgentToolPort protocol and exposes a JSON schema
for the Claude tool-use API.  Tools are thin wrappers around existing
repository and service ports — they never contain business logic themselves.
"""

from __future__ import annotations

from domain.ports.migration_ports import MigrationTaskRepositoryPort
from domain.ports.repository_ports import (
    CustomObjectRepositoryPort,
    ProgrammeRepositoryPort,
)

# ---------------------------------------------------------------------------
# check_programme_status
# ---------------------------------------------------------------------------


class CheckProgrammeStatusTool:
    """Reads programme details including status, complexity score, and metadata."""

    name: str = "check_programme_status"
    description: str = (
        "Retrieve the current status and details of a migration programme. "
        "Returns the programme's status, SAP versions, complexity score, and go-live date."
    )
    input_schema: dict = {
        "type": "object",
        "properties": {
            "programme_id": {
                "type": "string",
                "description": "The unique identifier of the programme.",
            },
        },
        "required": ["programme_id"],
    }

    def __init__(self, programme_repo: ProgrammeRepositoryPort) -> None:
        self._programme_repo = programme_repo

    async def execute(self, params: dict) -> dict:
        programme_id = params["programme_id"]
        programme = await self._programme_repo.get_by_id(programme_id)
        if programme is None:
            return {"error": f"Programme '{programme_id}' not found."}
        return {
            "id": programme.id,
            "name": programme.name,
            "customer_id": programme.customer_id,
            "status": programme.status.value,
            "sap_source_version": programme.sap_source_version,
            "target_version": programme.target_version,
            "go_live_date": programme.go_live_date.isoformat() if programme.go_live_date else None,
            "complexity_score": programme.complexity_score.score if programme.complexity_score else None,
        }


# ---------------------------------------------------------------------------
# list_custom_objects
# ---------------------------------------------------------------------------


class ListCustomObjectsTool:
    """Lists ABAP custom objects for a landscape."""

    name: str = "list_custom_objects"
    description: str = (
        "List all ABAP custom objects for a given landscape. "
        "Returns object names, types, compatibility status, and deprecated APIs."
    )
    input_schema: dict = {
        "type": "object",
        "properties": {
            "landscape_id": {
                "type": "string",
                "description": "The unique identifier of the SAP landscape.",
            },
        },
        "required": ["landscape_id"],
    }

    def __init__(self, object_repo: CustomObjectRepositoryPort) -> None:
        self._object_repo = object_repo

    async def execute(self, params: dict) -> dict:
        landscape_id = params["landscape_id"]
        objects = await self._object_repo.list_by_landscape(landscape_id)
        if not objects:
            return {"objects": [], "total": 0}
        return {
            "total": len(objects),
            "objects": [
                {
                    "id": obj.id,
                    "object_name": obj.object_name,
                    "object_type": obj.object_type.value,
                    "package_name": obj.package_name,
                    "compatibility_status": obj.compatibility_status.value if obj.compatibility_status else None,
                    "deprecated_apis": list(obj.deprecated_apis) if obj.deprecated_apis else [],
                }
                for obj in objects
            ],
        }


# ---------------------------------------------------------------------------
# run_analysis
# ---------------------------------------------------------------------------


class RunAnalysisTool:
    """Triggers ABAP analysis on custom objects for a landscape."""

    name: str = "run_analysis"
    description: str = (
        "Trigger AI-powered ABAP compatibility analysis on all custom objects "
        "within a landscape.  Returns a summary of compatible, incompatible, "
        "and needs-review counts.  This is an expensive operation."
    )
    input_schema: dict = {
        "type": "object",
        "properties": {
            "landscape_id": {
                "type": "string",
                "description": "The landscape to analyse.",
            },
            "programme_id": {
                "type": "string",
                "description": "The programme that owns this landscape.",
            },
        },
        "required": ["landscape_id", "programme_id"],
    }

    def __init__(self, analysis_use_case: object) -> None:
        # We accept the RunABAPAnalysisUseCase — typed as object to avoid
        # circular imports.  The use case must have an `execute` method.
        self._analysis_use_case = analysis_use_case

    async def execute(self, params: dict) -> dict:
        landscape_id = params["landscape_id"]
        programme_id = params["programme_id"]
        try:
            result = await self._analysis_use_case.execute(  # type: ignore[attr-defined]
                landscape_id=landscape_id,
                programme_id=programme_id,
            )
            return {
                "programme_id": result.programme_id,
                "total_objects": result.total_objects,
                "compatible_count": result.compatible_count,
                "incompatible_count": result.incompatible_count,
                "needs_review_count": result.needs_review_count,
            }
        except Exception as exc:
            return {"error": f"Analysis failed: {exc}"}


# ---------------------------------------------------------------------------
# check_data_readiness
# ---------------------------------------------------------------------------


class CheckDataReadinessTool:
    """Reads data profiling results for a programme."""

    name: str = "check_data_readiness"
    description: str = (
        "Check the data readiness / profiling results for a programme. "
        "Returns data quality scores and domain summaries if profiling has been run."
    )
    input_schema: dict = {
        "type": "object",
        "properties": {
            "programme_id": {
                "type": "string",
                "description": "The programme to check data readiness for.",
            },
        },
        "required": ["programme_id"],
    }

    def __init__(self, data_profiling_query: object) -> None:
        self._data_profiling_query = data_profiling_query

    async def execute(self, params: dict) -> dict:
        programme_id = params["programme_id"]
        try:
            result = await self._data_profiling_query.execute(  # type: ignore[attr-defined]
                programme_id=programme_id,
            )
            # Return whatever the query gives us as a dict
            if hasattr(result, "model_dump"):
                return result.model_dump()
            return {"programme_id": programme_id, "result": str(result)}
        except Exception as exc:
            return {"error": f"Data readiness check failed: {exc}"}


# ---------------------------------------------------------------------------
# generate_test_scenarios
# ---------------------------------------------------------------------------


class GenerateTestScenariosTool:
    """Triggers AI test scenario generation for a programme."""

    name: str = "generate_test_scenarios"
    description: str = (
        "Generate AI-powered test scenarios for the custom objects in a programme. "
        "Returns the number of test scenarios created."
    )
    input_schema: dict = {
        "type": "object",
        "properties": {
            "programme_id": {
                "type": "string",
                "description": "The programme to generate test scenarios for.",
            },
            "landscape_id": {
                "type": "string",
                "description": "The landscape whose objects to generate tests for.",
            },
        },
        "required": ["programme_id", "landscape_id"],
    }

    def __init__(self, test_generation_use_case: object) -> None:
        self._test_generation_use_case = test_generation_use_case

    async def execute(self, params: dict) -> dict:
        programme_id = params["programme_id"]
        landscape_id = params["landscape_id"]
        try:
            result = await self._test_generation_use_case.execute(  # type: ignore[attr-defined]
                programme_id=programme_id,
                landscape_id=landscape_id,
            )
            if hasattr(result, "model_dump"):
                return result.model_dump()
            return {"programme_id": programme_id, "result": str(result)}
        except Exception as exc:
            return {"error": f"Test generation failed: {exc}"}


# ---------------------------------------------------------------------------
# check_migration_status
# ---------------------------------------------------------------------------


class CheckMigrationStatusTool:
    """Reads migration task statuses for a programme."""

    name: str = "check_migration_status"
    description: str = (
        "Check the migration execution status for a programme. "
        "Returns a summary of task counts by status and the list of tasks."
    )
    input_schema: dict = {
        "type": "object",
        "properties": {
            "programme_id": {
                "type": "string",
                "description": "The programme to check migration status for.",
            },
        },
        "required": ["programme_id"],
    }

    def __init__(self, task_repo: MigrationTaskRepositoryPort) -> None:
        self._task_repo = task_repo

    async def execute(self, params: dict) -> dict:
        programme_id = params["programme_id"]
        tasks = await self._task_repo.list_by_programme(programme_id)
        if not tasks:
            return {"programme_id": programme_id, "total_tasks": 0, "tasks": []}

        status_counts: dict[str, int] = {}
        task_summaries = []
        for task in tasks:
            status_val = task.status.value
            status_counts[status_val] = status_counts.get(status_val, 0) + 1
            task_summaries.append({
                "id": task.id,
                "task_name": task.task_name,
                "task_type": task.task_type.value,
                "status": status_val,
                "error_message": task.error_message,
            })

        return {
            "programme_id": programme_id,
            "total_tasks": len(tasks),
            "status_counts": status_counts,
            "tasks": task_summaries,
        }
