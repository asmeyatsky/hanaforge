"""InMemoryAnomalyRepository — dev-mode in-memory implementation of AnomalyRepositoryPort."""

from __future__ import annotations

from datetime import datetime

from domain.value_objects.migration_types import (
    AnomalyAlert,
    AnomalyType,
    AuditSeverity,
)


class InMemoryAnomalyRepository:
    """Implements AnomalyRepositoryPort using a plain Python dict."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    async def save(self, alert: AnomalyAlert) -> None:
        self._store[alert.id] = self._to_dict(alert)

    async def list_active(self, programme_id: str) -> list[AnomalyAlert]:
        return [
            self._from_dict(data)
            for data in self._store.values()
            if data["programme_id"] == programme_id and not data["acknowledged"]
        ]

    async def acknowledge(self, alert_id: str) -> None:
        data = self._store.get(alert_id)
        if data is not None:
            data["acknowledged"] = True
