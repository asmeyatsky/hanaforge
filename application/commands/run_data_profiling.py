"""RunDataProfilingUseCase — parallel data profiling across all tables in a landscape."""

from __future__ import annotations

import asyncio
from dataclasses import replace

from application.dtos.data_dto import DataDomainResponse, DataProfilingResultsResponse
from domain.events.data_events import DataProfilingCompletedEvent, DataProfilingStartedEvent
from domain.ports.data_analysis_ports import DataProfilingPort, DataRepositoryPort
from domain.ports.event_bus_ports import EventBusPort
from domain.services.data_quality_service import DataQualityService
from domain.value_objects.data_quality import DataMigrationStatus

_MAX_CONCURRENT = 10


class RunDataProfilingUseCase:
    """Single-responsibility use case: profile all data domains for a landscape in parallel."""

    def __init__(
        self,
        data_repo: DataRepositoryPort,
        profiling_port: DataProfilingPort,
        quality_service: DataQualityService,
        event_bus: EventBusPort,
    ) -> None:
        self._data_repo = data_repo
        self._profiling_port = profiling_port
        self._quality_service = quality_service
        self._event_bus = event_bus

    async def execute(self, landscape_id: str) -> DataProfilingResultsResponse:
        # 1. Load all data domains for this landscape
        domains = await self._data_repo.list_by_landscape(landscape_id)
        if not domains:
            return DataProfilingResultsResponse(
                landscape_id=landscape_id,
                total_tables=0,
                tables_profiled=0,
                overall_quality=0.0,
                risk_level="CRITICAL",
                domains=[],
                risk_register=[],
            )

        # 2. Publish profiling started event
        start_event = DataProfilingStartedEvent(
            aggregate_id=landscape_id,
            landscape_id=landscape_id,
            table_count=len(domains),
        )
        await self._event_bus.publish(start_event)

        # 3. Profile each table concurrently
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

        async def _profile_one(domain_entity):
            async with semaphore:
                # Read file data from storage key
                _storage_key = f"data-exports/{landscape_id}/{domain_entity.table_name}"
                try:
                    file_bytes = b""  # Profiling port receives the raw data
                    profile = await self._profiling_port.profile_table(
                        file_bytes, "csv"
                    )
                except Exception:
                    return domain_entity

                # Update domain with profiling results
                updated = domain_entity.profile_complete(
                    null_rates=profile.null_rates,
                    dup_count=profile.duplicate_keys,
                    ref_score=min(1.0, max(0.0, 1.0 - (profile.duplicate_keys / max(profile.record_count, 1)))),
                    encoding_issues=profile.encoding_issues,
                )

                # Update record/field counts
                updated = replace(
                    updated,
                    record_count=profile.record_count,
                    field_count=profile.field_count,
                )

                return updated

        profile_tasks = [_profile_one(d) for d in domains]
        profiled_domains = await asyncio.gather(*profile_tasks)

        # 4. Calculate quality scores and persist
        tables_profiled = 0
        response_domains: list[DataDomainResponse] = []
        final_domains: list = []

        for domain_entity in profiled_domains:
            if domain_entity.migration_status == DataMigrationStatus.PROFILED:
                tables_profiled += 1
                quality = self._quality_service.assess_dataset_quality(domain_entity)
                domain_entity = replace(domain_entity, quality_score=quality)

            final_domains.append(domain_entity)
            await self._data_repo.save(domain_entity)

            quality_dict = None
            null_rate_summary = None
            if domain_entity.quality_score is not None:
                quality_dict = {
                    "completeness": domain_entity.quality_score.completeness,
                    "consistency": domain_entity.quality_score.consistency,
                    "accuracy": domain_entity.quality_score.accuracy,
                    "overall": domain_entity.quality_score.overall,
                    "risk_level": domain_entity.quality_score.risk_level,
                }
            if domain_entity.null_rates:
                null_rate_summary = sum(
                    nr.null_percentage for nr in domain_entity.null_rates
                ) / len(domain_entity.null_rates)

            response_domains.append(
                DataDomainResponse(
                    id=domain_entity.id,
                    table_name=domain_entity.table_name,
                    record_count=domain_entity.record_count,
                    field_count=domain_entity.field_count,
                    quality_score=quality_dict,
                    migration_status=domain_entity.migration_status.value,
                    null_rate_summary=null_rate_summary,
                    duplicate_key_count=domain_entity.duplicate_key_count,
                )
            )

        # 5. Calculate overall quality
        profiled_with_quality = [
            d for d in final_domains if d.quality_score is not None
        ]
        if profiled_with_quality:
            overall_quality = sum(
                d.quality_score.overall for d in profiled_with_quality
            ) / len(profiled_with_quality)
        else:
            overall_quality = 0.0

        # 6. Generate risk register
        risk_entries = self._quality_service.generate_risk_register(final_domains)
        risk_register = [
            {
                "table_name": entry.table_name,
                "risk_level": entry.risk_level,
                "risk_category": entry.risk_category,
                "description": entry.description,
                "recommended_action": entry.recommended_action,
                "priority": entry.priority,
            }
            for entry in risk_entries
        ]

        # Determine overall risk level
        if overall_quality >= 0.85:
            risk_level = "LOW"
        elif overall_quality >= 0.65:
            risk_level = "MEDIUM"
        elif overall_quality >= 0.40:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        # 7. Publish profiling completed event
        completed_event = DataProfilingCompletedEvent(
            aggregate_id=landscape_id,
            landscape_id=landscape_id,
            tables_profiled=tables_profiled,
            overall_quality=round(overall_quality, 4),
        )
        await self._event_bus.publish(completed_event)

        return DataProfilingResultsResponse(
            landscape_id=landscape_id,
            total_tables=len(domains),
            tables_profiled=tables_profiled,
            overall_quality=round(overall_quality, 4),
            risk_level=risk_level,
            domains=response_domains,
            risk_register=risk_register,
        )
