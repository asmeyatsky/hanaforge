"""Domain exception hierarchy — structured errors for the HanaForge domain layer.

All domain exceptions inherit from ``DomainError`` and carry a machine-readable
``code``, a human-readable ``message``, and an optional ``details`` dict.
Application and presentation layers map these to appropriate HTTP responses.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-level errors.

    Attributes:
        message: Human-readable description of the error.
        code: Machine-readable error code (e.g. ``"DOMAIN_ERROR"``).
        details: Arbitrary key/value pairs providing additional context.
    """

    def __init__(
        self,
        message: str,
        code: str = "DOMAIN_ERROR",
        details: dict | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class EntityNotFoundError(DomainError):
    """Raised when a requested entity does not exist in the repository."""

    def __init__(
        self,
        message: str = "Entity not found",
        code: str = "ENTITY_NOT_FOUND",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class ValidationError(DomainError):
    """Raised when domain validation rules are violated (e.g. invalid value objects)."""

    def __init__(
        self,
        message: str = "Validation failed",
        code: str = "VALIDATION_ERROR",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class BusinessRuleViolationError(DomainError):
    """Raised when a business invariant or state-transition rule is violated."""

    def __init__(
        self,
        message: str = "Business rule violation",
        code: str = "BUSINESS_RULE_VIOLATION",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class ConflictError(DomainError):
    """Raised on conflicts such as duplicate creation or optimistic-lock failures."""

    def __init__(
        self,
        message: str = "Conflict",
        code: str = "CONFLICT",
        details: dict | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)
