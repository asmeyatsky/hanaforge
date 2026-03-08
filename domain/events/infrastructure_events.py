"""Infrastructure provisioning domain events — GCP landing zone lifecycle."""

from __future__ import annotations

from dataclasses import dataclass

from domain.events.event_base import DomainEvent


@dataclass(frozen=True)
class InfrastructurePlanCreatedEvent(DomainEvent):
    programme_id: str = ""
    region: str = ""


@dataclass(frozen=True)
class TerraformPlanGeneratedEvent(DomainEvent):
    programme_id: str = ""
    plan_ref: str = ""


@dataclass(frozen=True)
class PlanValidatedEvent(DomainEvent):
    programme_id: str = ""
    status: str = ""
    checks_passed: int = 0
    checks_failed: int = 0


@dataclass(frozen=True)
class CostModelGeneratedEvent(DomainEvent):
    programme_id: str = ""
    total_monthly: float = 0.0


@dataclass(frozen=True)
class ProvisioningStartedEvent(DomainEvent):
    programme_id: str = ""


@dataclass(frozen=True)
class ProvisioningCompletedEvent(DomainEvent):
    programme_id: str = ""
    duration_minutes: int = 0
