"""Firestore-backed DataDomainRepository — production implementation for M03."""

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
from infrastructure.repositories.firestore_base import FirestoreBase

COLLECTION = "data_domains"


class FirestoreDataDomainRepository(FirestoreBase):
    """Implements DataRepositoryPort using Firestore."""

    @staticmethod
    def _to_dict(dd: DataDomain) -> dict:
        null_rates = [
            {"field_name": nr.field_name, "null_count": nr.null_count, "total_count": nr.total_count}
            for nr in dd.null_rates
        ]
        quality = None
        if dd.quality_score is not None:
            quality = {
                "completeness": dd.quality_score.completeness,
                "consistency": dd.quality_score.consistency,
                "accuracy": dd.quality_score.accuracy,
            }
        rules = [
            {
                "source_field": r.source_field,
                "target_field": r.target_field,
                "rule_type": r.rule_type.value,
                "rule_expression": r.rule_expression,
                "description": r.description,
            }
            for r in dd.transformation_rules
        ]
        return {
            "id": dd.id,
            "landscape_id": dd.landscape_id,
            "table_name": dd.table_name,
            "record_count": dd.record_count,
            "field_count": dd.field_count,
            "null_rates": null_rates,
            "duplicate_key_count": dd.duplicate_key_count,
            "referential_integrity_score": dd.referential_integrity_score,
            "encoding_issues": list(dd.encoding_issues),
            "migration_status": dd.migration_status.value,
            "transformation_rules": rules,
            "quality_score": quality,
            "created_at": dd.created_at.isoformat(),
        }

    @staticmethod
    def _from_dict(data: dict) -> DataDomain:
        null_rates = tuple(
            FieldNullRate(field_name=nr["field_name"], null_count=nr["null_count"], total_count=nr["total_count"])
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

    async def save(self, data_domain: DataDomain) -> None:
        await self._doc(COLLECTION, data_domain.id).set(self._to_dict(data_domain))

    async def get_by_id(self, id: str) -> DataDomain | None:
        doc = await self._doc(COLLECTION, id).get()
        if not doc.exists:
            return None
        return self._from_dict(doc.to_dict())

    async def list_by_landscape(self, landscape_id: str) -> list[DataDomain]:
        query = self._collection(COLLECTION).where("landscape_id", "==", landscape_id)
        return [self._from_dict(doc.to_dict()) async for doc in query.stream()]

    async def get_by_table_name(self, landscape_id: str, table_name: str) -> DataDomain | None:
        query = (
            self._collection(COLLECTION)
            .where("landscape_id", "==", landscape_id)
            .where("table_name", "==", table_name)
        )
        async for doc in query.stream():
            return self._from_dict(doc.to_dict())
        return None
