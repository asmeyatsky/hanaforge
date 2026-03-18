"""GenerateBoardPresentationUseCase — produces a board-level scope document."""

from __future__ import annotations

from domain.ports import (
    CustomObjectRepositoryPort,
    LandscapeRepositoryPort,
    ProgrammeRepositoryPort,
    RemediationRepositoryPort,
    ReportGeneratorPort,
)
from domain.value_objects.complexity_score import ComplexityScore


class GenerateBoardPresentationUseCase:
    """Single-responsibility use case: generate a board-presentation scope document."""

    def __init__(
        self,
        programme_repo: ProgrammeRepositoryPort,
        landscape_repo: LandscapeRepositoryPort,
        object_repo: CustomObjectRepositoryPort,
        remediation_repo: RemediationRepositoryPort,
        report_generator: ReportGeneratorPort,
    ) -> None:
        self._programme_repo = programme_repo
        self._landscape_repo = landscape_repo
        self._object_repo = object_repo
        self._remediation_repo = remediation_repo
        self._report_generator = report_generator

    async def execute(self, programme_id: str) -> bytes:
        # 1. Load programme
        programme = await self._programme_repo.get_by_id(programme_id)
        if programme is None:
            raise ValueError(f"Programme {programme_id} not found")

        # 2. Load landscapes for this programme
        landscapes = await self._landscape_repo.list_by_programme(programme_id)

        # 3. Load all custom objects across landscapes
        objects = []
        for ls in landscapes:
            ls_objects = await self._object_repo.get_by_landscape(ls.id)
            objects.extend(ls_objects)

        # 4. Load remediations
        object_ids = [o.id for o in objects]
        remediations = (
            await self._remediation_repo.get_by_object_ids(object_ids)
            if object_ids
            else []
        )

        # 5. Compute or reuse complexity score
        if programme.complexity_score is not None:
            complexity = programme.complexity_score
        else:
            # Derive a basic complexity score from object counts
            total = len(objects)
            incompatible = sum(
                1
                for o in objects
                if getattr(o, "compatibility_status", None)
                and o.compatibility_status.value == "INCOMPATIBLE"
            )
            score = min(100, max(1, int(30 + (incompatible / max(total, 1)) * 70)))
            complexity = ComplexityScore(score=score)

        # 6. Build recommendation text
        recommendation = _build_recommendation(complexity, programme)

        # 7. Generate the HTML document
        return await self._report_generator.generate_board_presentation(
            programme=programme,
            landscapes=landscapes,
            objects=objects,
            remediations=remediations,
            complexity=complexity,
            recommendation=recommendation,
        )


def _build_recommendation(complexity: ComplexityScore, programme: object) -> str:
    """Return a migration approach recommendation string based on complexity."""
    source = getattr(programme, "sap_source_version", "ECC")
    target = getattr(programme, "target_version", "S/4HANA")

    if complexity.risk_level == "CRITICAL":
        return (
            f"Given the CRITICAL complexity rating, a multi-phase brownfield "
            f"migration from {source} to {target} is recommended.  The programme "
            f"should include dedicated remediation sprints, parallel testing "
            f"cycles, and a phased cutover strategy with executive-level "
            f"governance gates at each milestone."
        )
    if complexity.risk_level == "HIGH":
        return (
            f"A phased brownfield migration from {source} to {target} is "
            f"recommended.  Additional buffer time should be allocated for "
            f"remediation of incompatible custom objects and comprehensive "
            f"integration testing.  Senior ABAP developers should be retained "
            f"throughout the programme."
        )
    if complexity.risk_level == "MEDIUM":
        return (
            f"A standard brownfield migration from {source} to {target} is "
            f"recommended.  AI-assisted remediation can accelerate resolution "
            f"of incompatible custom code.  Standard testing and cutover "
            f"procedures should be sufficient with proper planning."
        )
    return (
        f"An accelerated brownfield migration from {source} to {target} is "
        f"feasible.  The low complexity score indicates minimal custom code "
        f"remediation.  AI-assisted tooling can further compress the timeline."
    )
