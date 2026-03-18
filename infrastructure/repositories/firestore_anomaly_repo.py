"""Firestore-backed AnomalyRepository — production implementation for M06."""

from __future__ import annotations

from datetime import datetime

from domain.value_objects.migration_types import AnomalyAlert, AnomalyType, AuditSeverity
from infrastructure.repositories.firestore_base import FirestoreBase

COLLECTION = "anomaly_alerts"


class FirestoreAnomalyRepository(FirestoreBase):
    """Implements AnomalyRepositoryPort using Firestore."""

    @staticmethod
    def _to_dict(alert: AnomalyAlert) -> dict:
        return {
            "id": alert.id,
            "programme_id": alert.programme_id,
            "task_id": alert.task_id,
            "alert_type": alert.alert_type.value,
            "severity": alert.severity.value,
            "message": alert.message,
            "detected_at": alert.detected_at.isoformat(),
            "metric_name": alert.metric_name,
            "expected_value": alert.expected_value,
            "actual_value": alert.actual_value,
            "acknowledged": alert.acknowledged,
        }

    @staticmethod
    def _from_dict(data: dict) -> AnomalyAlert:
        return AnomalyAlert(
            id=data["id"],
            programme_id=data["programme_id"],
            task_id=data["task_id"],
            alert_type=AnomalyType(data["alert_type"]),
            severity=AuditSeverity(data["severity"]),
            message=data["message"],
            detected_at=datetime.fromisoformat(data["detected_at"]),
            metric_name=data["metric_name"],
            expected_value=data["expected_value"],
            actual_value=data["actual_value"],
            acknowledged=data["acknowledged"],
        )

    async def save(self, alert: AnomalyAlert) -> None:
        await self._doc(COLLECTION, alert.id).set(self._to_dict(alert))

    async def list_active(self, programme_id: str) -> list[AnomalyAlert]:
        query = (
            self._collection(COLLECTION).where("programme_id", "==", programme_id).where("acknowledged", "==", False)
        )
        return [self._from_dict(doc.to_dict()) async for doc in query.stream()]

    async def acknowledge(self, alert_id: str) -> None:
        await self._doc(COLLECTION, alert_id).update({"acknowledged": True})
