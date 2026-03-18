"""GenerateTransformationRulesUseCase — AI-generated LTMC-compatible transformation rules."""

from __future__ import annotations

from domain.events.data_events import TransformationRulesGeneratedEvent
from domain.ports.data_analysis_ports import DataRepositoryPort, DataTransformationPort
from domain.ports.event_bus_ports import EventBusPort
from domain.value_objects.data_quality import TransformationRule


class GenerateTransformationRulesUseCase:
    """Single-responsibility use case: generate data transformation rules via AI."""

    def __init__(
        self,
        data_repo: DataRepositoryPort,
        transformation_port: DataTransformationPort,
        event_bus: EventBusPort,
    ) -> None:
        self._data_repo = data_repo
        self._transformation_port = transformation_port
        self._event_bus = event_bus

    async def execute(
        self,
        landscape_id: str,
        table_name: str,
    ) -> list[TransformationRule]:
        # 1. Load the data domain
        data_domain = await self._data_repo.get_by_table_name(landscape_id, table_name)
        if data_domain is None:
            raise ValueError(
                f"DataDomain for table {table_name!r} in landscape "
                f"{landscape_id!r} not found"
            )

        # 2. Build source schema from profiled data
        source_schema = {
            "table_name": data_domain.table_name,
            "fields": [nr.field_name for nr in data_domain.null_rates],
            "record_count": data_domain.record_count,
        }

        # 3. Define target schema (S/4HANA target)
        target_schema = {
            "table_name": data_domain.table_name,
            "target_version": "S/4HANA",
        }

        # 4. Generate rules via AI
        sample_data: list[dict] = []
        rules = await self._transformation_port.generate_rules(
            source_schema=source_schema,
            target_schema=target_schema,
            sample_data=sample_data,
        )

        # 5. Add rules to domain entity and persist
        updated = data_domain
        for rule in rules:
            updated = updated.add_transformation_rule(rule)
        await self._data_repo.save(updated)

        # 6. Publish event
        event = TransformationRulesGeneratedEvent(
            aggregate_id=landscape_id,
            landscape_id=landscape_id,
            rule_count=len(rules),
        )
        await self._event_bus.publish(event)

        return rules
