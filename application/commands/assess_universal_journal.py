"""AssessUniversalJournalUseCase — evaluates ACDOCA migration readiness."""

from __future__ import annotations

from domain.ports.event_bus_ports import EventBusPort
from domain.services.universal_journal_service import UniversalJournalService
from domain.value_objects.data_quality import UniversalJournalAssessment


class AssessUniversalJournalUseCase:
    """Single-responsibility use case: assess Universal Journal migration readiness."""

    def __init__(
        self,
        uj_service: UniversalJournalService,
        event_bus: EventBusPort,
    ) -> None:
        self._uj_service = uj_service
        self._event_bus = event_bus

    async def execute(
        self,
        landscape_id: str,
        fi_config: dict,
        co_config: dict,
    ) -> UniversalJournalAssessment:
        # Run readiness assessment (pure domain logic)
        result = self._uj_service.assess_readiness(
            fi_config=fi_config,
            co_config=co_config,
        )

        return result
