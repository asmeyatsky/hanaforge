"""InMemoryDataRepository — dev-mode in-memory implementation of DataRepositoryPort."""

from __future__ import annotations

from datetime import datetime

from domain.entities.data_domain import DataDomain
from domain.value_objects.data_quality import (
    DataMigrationStatus,
    DataQualityScore,
    FieldNullRate,
    TransformationRule,
    TransformationRuleType,
)


class InMemoryDataRepository:
    """Implements DataRepositoryPort using a plain Python dict."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(data_domain: DataDomain) -> dict:
        null_rates = [
            {
                "field_name": nr.field_name,
                "null_count": nr.null_count,
                "total_count": nr.total_count,
            }
            for nr in data_domain.null_rates
        ]

        quality = None
        if data_domain.quality_score is not None:
            quality = {
                "completeness": data_domain.quality_score.completeness,
                "consistency": data_domain.quality_score.consistency,
                "accuracy": data_domain.quality_score.accuracy,
            }

        rules = [
            {
                "source_field": r.source_field,
                "target_field": r.target_field,
                "rule_type": r.rule_type.value,
                "rule_expression": r.rule_expression,
                "description": r.description,
            }
            for r in data_domain.transformation_rules
        ]

        return {
            "id": data_domain.id,
            "landscape_id": data_domain.landscape_id,
            "table_name": data_domain.table_name,
            "record_count": data_domain.record_count,
            "field_count": data_domain.field_count,
            "null_rates": null_rates,
            "duplicate_key_count": data_domain.duplicate_key_count,
            "referential_integrity_score": data_domain.referential_integrity_score,
            "encoding_issues": list(data_domain.encoding_issues),
            "migration_status": data_domain.migration_status.value,
            "transformation_rules": rules,
            "quality_score": quality,
            "created_at": data_domain.created_at.isoformat(),
        }

    @staticmethod
    def _from_dict(data: dict) -> DataDomain:
        null_rates = tuple(
            FieldNullRate(
                field_name=nr["field_name"],
                null_count=nr["null_count"],
                total_count=nr["total_count"],
            )
            for nr in data["null_rates"]
        )

        quality = None
        if data["quality_score"] is not None:
            quality = DataQualityScore(
                completeness=data["quality_score"]["completeness"],
                consistency=data["quality_score"]["consistency"],
                accuracy=data["quality_score"]["accuracy"],
            )

        rules = tuple(
            TransformationRule(
                source_field=r["source_field"],
                target_field=r["target_field"],
                rule_type=TransformationRuleType(r["rule_type"]),
                rule_expression=r["rule_expression"],
                description=r["description"],
            )
            for r in data["transformation_rules"]
        )

        return DataDomain(
            id=data["id"],
            landscape_id=data["landscape_id"],
            table_name=data["table_name"],
            record_count=data["record_count"],
            field_count=data["field_count"],
            null_rates=null_rates,
            duplicate_key_count=data["duplicate_key_count"],
            referential_integrity_score=data["referential_integrity_score"],
            encoding_issues=tuple(data["encoding_issues"]),
            migration_status=DataMigrationStatus(data["migration_status"]),
            transformation_rules=rules,
            quality_score=quality,
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    async def save(self, data_domain: DataDomain) -> None:
        self._store[data_domain.id] = self._to_dict(data_domain)

    async def get_by_id(self, id: str) -> DataDomain | None:
        data = self._store.get(id)
        if data is None:
            return None
        return self._from_dict(data)

    async def list_by_landscape(self, landscape_id: str) -> list[DataDomain]:
        return [
            self._from_dict(data)
            for data in self._store.values()
            if data["landscape_id"] == landscape_id
        ]

    async def get_by_table_name(
        self, landscape_id: str, table_name: str
    ) -> DataDomain | None:
        for data in self._store.values():
            if (
                data["landscape_id"] == landscape_id
                and data["table_name"] == table_name
            ):
                return self._from_dict(data)
        return None
