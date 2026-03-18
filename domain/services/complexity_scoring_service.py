"""Complexity scoring — pure domain logic that quantifies migration risk."""

from __future__ import annotations

from domain.entities.custom_object import CustomObject
from domain.entities.sap_landscape import SAPLandscape
from domain.value_objects.complexity_score import ComplexityScore
from domain.value_objects.object_type import CompatibilityStatus


class ComplexityScoringService:
    _WEIGHT_CUSTOM_OBJECTS = 0.30
    _WEIGHT_INCOMPATIBLE_RATIO = 0.35
    _WEIGHT_DB_SIZE = 0.20
    _WEIGHT_USER_COUNT = 0.15

    async def calculate(
        self,
        custom_objects: list[dict],
        integration_points: list[dict],
    ) -> ComplexityScore:
        """Calculate complexity from raw discovery data (dicts, not entities).

        Used by the DiscoveryWorkflow DAG before entities are fully constructed.
        """
        obj_count = len(custom_objects)
        integration_count = len(integration_points)

        object_score = self._score_custom_object_count(obj_count)
        # Estimate integration complexity as a proxy for incompatible ratio
        integration_score = min(100.0, integration_count * 8.0) if integration_count else 10.0

        weighted = object_score * 0.45 + integration_score * 0.55

        final = max(1, min(100, round(weighted)))
        return ComplexityScore(score=final)

    def calculate_landscape_complexity(
        self,
        landscape: SAPLandscape,
        objects: list[CustomObject],
    ) -> ComplexityScore:
        object_score = self._score_custom_object_count(landscape.custom_object_count)
        incompatible_ratio_score = self._score_incompatible_ratio(objects)
        db_score = self._score_db_size(landscape.db_size_gb)
        user_score = self._score_user_count(landscape.number_of_users)

        weighted = (
            object_score * self._WEIGHT_CUSTOM_OBJECTS
            + incompatible_ratio_score * self._WEIGHT_INCOMPATIBLE_RATIO
            + db_score * self._WEIGHT_DB_SIZE
            + user_score * self._WEIGHT_USER_COUNT
        )

        final = max(1, min(100, round(weighted)))
        return ComplexityScore(score=final)

    @staticmethod
    def _score_custom_object_count(count: int) -> float:
        if count <= 100:
            return 10.0
        if count <= 500:
            return 30.0
        if count <= 2000:
            return 55.0
        if count <= 5000:
            return 75.0
        return 95.0

    @staticmethod
    def _score_incompatible_ratio(objects: list[CustomObject]) -> float:
        if not objects:
            return 10.0
        incompatible = sum(1 for o in objects if o.compatibility_status == CompatibilityStatus.INCOMPATIBLE)
        ratio = incompatible / len(objects)
        return max(1.0, min(100.0, ratio * 100))

    @staticmethod
    def _score_db_size(db_size_gb: float) -> float:
        if db_size_gb <= 100:
            return 10.0
        if db_size_gb <= 500:
            return 30.0
        if db_size_gb <= 2000:
            return 55.0
        if db_size_gb <= 10000:
            return 75.0
        return 95.0

    @staticmethod
    def _score_user_count(users: int) -> float:
        if users <= 100:
            return 10.0
        if users <= 500:
            return 25.0
        if users <= 2000:
            return 45.0
        if users <= 10000:
            return 70.0
        return 90.0
