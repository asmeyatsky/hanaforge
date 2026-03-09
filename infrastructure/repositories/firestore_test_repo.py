"""Firestore-backed TestScenario & TestSuite repositories — production implementation for M04."""

from __future__ import annotations

from domain.entities.test_scenario import TestScenario
from domain.entities.test_suite import TestSuite
from domain.value_objects.test_types import ProcessArea, TestStatus
from infrastructure.repositories.firestore_base import FirestoreBase

SCENARIOS_COLLECTION = "test_scenarios"
SUITES_COLLECTION = "test_suites"


class FirestoreTestScenarioRepository(FirestoreBase):
    """Implements TestScenarioRepositoryPort using Firestore.

    TestScenario is a frozen dataclass stored directly (Firestore handles
    dataclass-to-dict via __dict__ extraction).
    """

    @staticmethod
    def _to_dict(scenario: TestScenario) -> dict:
        d = {}
        for field in scenario.__dataclass_fields__:
            val = getattr(scenario, field)
            if isinstance(val, tuple):
                val = list(val)
            elif hasattr(val, "value"):
                val = val.value
            d[field] = val
        if "created_at" in d and hasattr(d["created_at"], "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
        return d

    @staticmethod
    def _from_doc(data: dict) -> TestScenario:
        from datetime import datetime

        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("process_area"), str):
            data["process_area"] = ProcessArea(data["process_area"])
        if isinstance(data.get("status"), str):
            data["status"] = TestStatus(data["status"])
        # Convert lists back to tuples for frozen dataclass
        for key in ("steps", "expected_results", "tags", "related_object_ids"):
            if key in data and isinstance(data[key], list):
                data[key] = tuple(data[key])
        return TestScenario(**data)

    async def save(self, scenario: TestScenario) -> None:
        await self._doc(SCENARIOS_COLLECTION, scenario.id).set(self._to_dict(scenario))

    async def save_batch(self, scenarios: list[TestScenario]) -> None:
        batch = self.client.batch()
        for s in scenarios:
            batch.set(self._doc(SCENARIOS_COLLECTION, s.id), self._to_dict(s))
        await batch.commit()

    async def get_by_id(self, id: str) -> TestScenario | None:
        doc = await self._doc(SCENARIOS_COLLECTION, id).get()
        if not doc.exists:
            return None
        return self._from_doc(doc.to_dict())

    async def list_by_programme(self, programme_id: str) -> list[TestScenario]:
        query = self._collection(SCENARIOS_COLLECTION).where("programme_id", "==", programme_id)
        return [self._from_doc(doc.to_dict()) async for doc in query.stream()]

    async def list_by_process_area(self, programme_id: str, process_area: ProcessArea) -> list[TestScenario]:
        query = (
            self._collection(SCENARIOS_COLLECTION)
            .where("programme_id", "==", programme_id)
            .where("process_area", "==", process_area.value)
        )
        return [self._from_doc(doc.to_dict()) async for doc in query.stream()]

    async def count_by_status(self, programme_id: str, status: TestStatus) -> int:
        query = (
            self._collection(SCENARIOS_COLLECTION)
            .where("programme_id", "==", programme_id)
            .where("status", "==", status.value)
        )
        count = 0
        async for _ in query.stream():
            count += 1
        return count


class FirestoreTestSuiteRepository(FirestoreBase):
    """Implements TestSuiteRepositoryPort using Firestore."""

    @staticmethod
    def _to_dict(suite: TestSuite) -> dict:
        d = {}
        for field in suite.__dataclass_fields__:
            val = getattr(suite, field)
            if isinstance(val, tuple):
                val = list(val)
            elif hasattr(val, "value"):
                val = val.value
            d[field] = val
        if "created_at" in d and hasattr(d["created_at"], "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
        return d

    @staticmethod
    def _from_doc(data: dict) -> TestSuite:
        from datetime import datetime

        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        for key in ("scenario_ids",):
            if key in data and isinstance(data[key], list):
                data[key] = tuple(data[key])
        return TestSuite(**data)

    async def save(self, suite: TestSuite) -> None:
        await self._doc(SUITES_COLLECTION, suite.id).set(self._to_dict(suite))

    async def get_by_id(self, id: str) -> TestSuite | None:
        doc = await self._doc(SUITES_COLLECTION, id).get()
        if not doc.exists:
            return None
        return self._from_doc(doc.to_dict())

    async def list_by_programme(self, programme_id: str) -> list[TestSuite]:
        query = self._collection(SUITES_COLLECTION).where("programme_id", "==", programme_id)
        return [self._from_doc(doc.to_dict()) async for doc in query.stream()]
