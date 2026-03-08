"""AssessBPConsolidationUseCase — evaluates Business Partner merge readiness."""

from __future__ import annotations

import csv
import io

from domain.events.data_events import BPConsolidationAssessedEvent
from domain.ports.event_bus_ports import EventBusPort
from domain.services.bp_consolidation_service import BPConsolidationService
from domain.value_objects.data_quality import BPConsolidationResult


class AssessBPConsolidationUseCase:
    """Single-responsibility use case: assess Customer/Vendor consolidation for BP model."""

    def __init__(
        self,
        bp_service: BPConsolidationService,
        event_bus: EventBusPort,
    ) -> None:
        self._bp_service = bp_service
        self._event_bus = event_bus

    async def execute(
        self,
        landscape_id: str,
        customer_file_bytes: bytes,
        vendor_file_bytes: bytes,
    ) -> BPConsolidationResult:
        # 1. Parse customer and vendor CSV data
        customer_records = self._parse_csv(customer_file_bytes)
        vendor_records = self._parse_csv(vendor_file_bytes)

        # 2. Run consolidation assessment (pure domain logic)
        result = self._bp_service.assess_consolidation(
            customer_records=customer_records,
            vendor_records=vendor_records,
        )

        # 3. Publish event
        event = BPConsolidationAssessedEvent(
            aggregate_id=landscape_id,
            landscape_id=landscape_id,
            merge_candidates=result.duplicate_pairs,
        )
        await self._event_bus.publish(event)

        return result

    @staticmethod
    def _parse_csv(file_bytes: bytes) -> list[dict]:
        """Parse CSV bytes into a list of dicts."""
        text = file_bytes.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
