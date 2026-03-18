"""GetDataProfilingResultsQuery — retrieves data profiling results for a landscape."""

from __future__ import annotations

from application.dtos.data_dto import DataDomainResponse, DataProfilingResultsResponse
from domain.ports.data_analysis_ports import DataRepositoryPort
from domain.services.data_quality_service import DataQualityService
from domain.value_objects.data_quality import DataMigrationStatus


class GetDataProfilingResultsQuery:
    """Read-only query: fetch data profiling results for all tables in a landscape."""

    def __init__(
        self,
        data_repo: DataRepositoryPort,
        quality_service: DataQualityService,
    ) -> None:
        self._data_repo = data_repo
        self._quality_service = quality_service

    async def execute(self, landscape_id: str) -> DataProfilingResultsResponse:
        domains = await self._data_repo.list_by_landscape(landscape_id)

        response_domains: list[DataDomainResponse] = []
        tables_profiled = 0

        for domain_entity in domains:
            if domain_entity.migration_status != DataMigrationStatus.NOT_PROFILED:
                tables_profiled += 1

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

        # Calculate overall quality
        profiled_with_quality = [
            d for d in domains if d.quality_score is not None
        ]
        if profiled_with_quality:
            overall_quality = sum(
                d.quality_score.overall for d in profiled_with_quality
            ) / len(profiled_with_quality)
        else:
            overall_quality = 0.0

        # Generate risk register
        risk_entries = self._quality_service.generate_risk_register(domains)
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

        return DataProfilingResultsResponse(
            landscape_id=landscape_id,
            total_tables=len(domains),
            tables_profiled=tables_profiled,
            overall_quality=round(overall_quality, 4),
            risk_level=risk_level,
            domains=response_domains,
            risk_register=risk_register,
        )
