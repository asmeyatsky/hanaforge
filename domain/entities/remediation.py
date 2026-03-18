"""Remediation suggestion entity — AI-generated fix proposals awaiting human review."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from domain.events.analysis_events import RemediationReviewedEvent
from domain.value_objects.object_type import ReviewStatus


@dataclass(frozen=True)
class RemediationSuggestion:
    id: str
    object_id: str
    issue_type: str
    deprecated_api: str
    suggested_replacement: str
    generated_code: str
    confidence_score: float
    reviewed_by: str | None
    status: ReviewStatus
    created_at: datetime

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError(
                f"confidence_score must be between 0 and 1, got {self.confidence_score}"
            )

    def approve(self, reviewer: str) -> RemediationSuggestion:
        if self.status != ReviewStatus.PENDING:
            raise ValueError(f"Cannot approve suggestion with status {self.status.value}")
        event = RemediationReviewedEvent(
            aggregate_id=self.id,
            object_id=self.object_id,
            approved=True,
            reviewer=reviewer,
        )
        return replace(self, status=ReviewStatus.APPROVED, reviewed_by=reviewer)

    def reject(self, reviewer: str) -> RemediationSuggestion:
        if self.status != ReviewStatus.PENDING:
            raise ValueError(f"Cannot reject suggestion with status {self.status.value}")
        event = RemediationReviewedEvent(
            aggregate_id=self.id,
            object_id=self.object_id,
            approved=False,
            reviewer=reviewer,
        )
        return replace(self, status=ReviewStatus.REJECTED, reviewed_by=reviewer)
