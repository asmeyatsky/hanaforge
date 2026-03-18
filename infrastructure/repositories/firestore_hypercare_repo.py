"""Firestore-backed HypercareRepository — production implementation for M07."""

from __future__ import annotations

from domain.entities.hypercare_session import HypercareSession
from domain.value_objects.cutover_types import HypercareStatus
from infrastructure.repositories.firestore_base import FirestoreBase

COLLECTION = "hypercare_sessions"


class FirestoreHypercareRepository(FirestoreBase):
    """Implements HypercareRepositoryPort using Firestore."""

    @staticmethod
    def _to_dict(session: HypercareSession) -> dict:
        d = {}
        for field in session.__dataclass_fields__:
            val = getattr(session, field)
            if isinstance(val, tuple):
                val = [
                    {
                        k: (v.value if hasattr(v, "value") else (v.isoformat() if hasattr(v, "isoformat") else v))
                        for k, v in item.__dict__.items()
                    }
                    if hasattr(item, "__dataclass_fields__")
                    else item
                    for item in val
                ]
            elif hasattr(val, "value") and isinstance(val.value, str):
                val = val.value
            elif hasattr(val, "isoformat"):
                val = val.isoformat()
            d[field] = val
        return d

    @staticmethod
    def _from_doc(data: dict) -> HypercareSession:
        from datetime import datetime

        from domain.value_objects.cutover_types import (
            HypercareIncident,
            HypercareStatus,
            IncidentSeverity,
        )

        for ts_field in ("started_at", "ended_at"):
            if isinstance(data.get(ts_field), str):
                data[ts_field] = datetime.fromisoformat(data[ts_field])

        if isinstance(data.get("status"), str):
            data["status"] = HypercareStatus(data["status"])

        if isinstance(data.get("incidents"), list):
            incidents = []
            for inc in data["incidents"]:
                if isinstance(inc, dict):
                    if isinstance(inc.get("severity"), str):
                        inc["severity"] = IncidentSeverity(inc["severity"])
                    if isinstance(inc.get("reported_at"), str):
                        inc["reported_at"] = datetime.fromisoformat(inc["reported_at"])
                    if isinstance(inc.get("resolved_at"), str):
                        inc["resolved_at"] = datetime.fromisoformat(inc["resolved_at"])
                    incidents.append(HypercareIncident(**inc))
                else:
                    incidents.append(inc)
            data["incidents"] = tuple(incidents)

        if isinstance(data.get("health_check_results"), list):
            data["health_check_results"] = tuple(data["health_check_results"])

        return HypercareSession(**data)

    async def save(self, session: HypercareSession) -> None:
        await self._doc(COLLECTION, session.id).set(self._to_dict(session))

    async def get_by_id(self, id: str) -> HypercareSession | None:
        doc = await self._doc(COLLECTION, id).get()
        if not doc.exists:
            return None
        return self._from_doc(doc.to_dict())

    async def get_active(self, programme_id: str) -> HypercareSession | None:
        active_statuses = [
            HypercareStatus.ACTIVE.value,
            HypercareStatus.MONITORING.value,
            HypercareStatus.ESCALATED.value,
        ]
        for status_val in active_statuses:
            query = (
                self._collection(COLLECTION)
                .where("programme_id", "==", programme_id)
                .where("status", "==", status_val)
                .limit(1)
            )
            async for doc in query.stream():
                return self._from_doc(doc.to_dict())
        return None
