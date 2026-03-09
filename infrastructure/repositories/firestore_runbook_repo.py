"""Firestore-backed RunbookRepository — production implementation for M07."""

from __future__ import annotations

from domain.entities.cutover_runbook import CutoverRunbook
from infrastructure.repositories.firestore_base import FirestoreBase

COLLECTION = "cutover_runbooks"


class FirestoreRunbookRepository(FirestoreBase):
    """Implements RunbookRepositoryPort using Firestore."""

    @staticmethod
    def _to_dict(rb: CutoverRunbook) -> dict:
        d = {}
        for field in rb.__dataclass_fields__:
            val = getattr(rb, field)
            if isinstance(val, tuple):
                val = [
                    {k: (v.value if hasattr(v, "value") else v) for k, v in item.__dict__.items()}
                    if hasattr(item, "__dict__") and hasattr(item, "__dataclass_fields__")
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
    def _from_doc(data: dict) -> CutoverRunbook:
        from datetime import datetime
        from domain.value_objects.cutover_types import ApprovalStatus, RunbookStep, StepCategory

        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("approval_status"), str):
            data["approval_status"] = ApprovalStatus(data["approval_status"])
        if isinstance(data.get("steps"), list):
            steps = []
            for s in data["steps"]:
                if isinstance(s, dict):
                    if isinstance(s.get("category"), str):
                        s["category"] = StepCategory(s["category"])
                    if "depends_on" in s and isinstance(s["depends_on"], list):
                        s["depends_on"] = tuple(s["depends_on"])
                    steps.append(RunbookStep(**s))
                else:
                    steps.append(s)
            data["steps"] = tuple(steps)
        return CutoverRunbook(**data)

    async def save(self, runbook: CutoverRunbook) -> None:
        await self._doc(COLLECTION, runbook.id).set(self._to_dict(runbook))

    async def get_by_id(self, id: str) -> CutoverRunbook | None:
        doc = await self._doc(COLLECTION, id).get()
        if not doc.exists:
            return None
        return self._from_doc(doc.to_dict())

    async def get_latest_by_programme(self, programme_id: str) -> CutoverRunbook | None:
        query = (
            self._collection(COLLECTION)
            .where("programme_id", "==", programme_id)
            .order_by("version", direction="DESCENDING")
            .limit(1)
        )
        async for doc in query.stream():
            return self._from_doc(doc.to_dict())
        return None

    async def list_by_programme(self, programme_id: str) -> list[CutoverRunbook]:
        query = self._collection(COLLECTION).where("programme_id", "==", programme_id)
        return [self._from_doc(doc.to_dict()) async for doc in query.stream()]
