"""Tests for the global error handler infrastructure.

Verifies that each ``DomainError`` subclass is mapped to the correct HTTP
status code and that the JSON error envelope is well-formed.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from domain.exceptions import (
    BusinessRuleViolationError,
    ConflictError,
    DomainError,
    EntityNotFoundError,
    ValidationError,
)
from presentation.api.error_handlers import register_error_handlers
from presentation.api.middleware.correlation_id import CorrelationIdMiddleware


# ---------------------------------------------------------------------------
# Fixture: build a minimal FastAPI app with error handlers + test routes
# ---------------------------------------------------------------------------
@pytest.fixture()
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.add_middleware(CorrelationIdMiddleware)
    register_error_handlers(test_app)

    @test_app.get("/raise-entity-not-found")
    async def _raise_entity_not_found() -> None:
        raise EntityNotFoundError(
            message="Programme 'abc' not found",
            details={"entity_type": "Programme", "entity_id": "abc"},
        )

    @test_app.get("/raise-validation")
    async def _raise_validation() -> None:
        raise ValidationError(
            message="Name must not be empty",
            details={"field": "name"},
        )

    @test_app.get("/raise-business-rule")
    async def _raise_business_rule() -> None:
        raise BusinessRuleViolationError(
            message="Cannot start analysis before discovery",
            details={"current_status": "CREATED"},
        )

    @test_app.get("/raise-conflict")
    async def _raise_conflict() -> None:
        raise ConflictError(
            message="Programme already exists",
            details={"duplicate_field": "name"},
        )

    @test_app.get("/raise-base-domain")
    async def _raise_base_domain() -> None:
        raise DomainError(message="Generic domain issue")

    @test_app.get("/raise-unhandled")
    async def _raise_unhandled() -> None:
        raise RuntimeError("something broke unexpectedly")

    return test_app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helper to validate the common envelope structure
# ---------------------------------------------------------------------------
def _assert_error_envelope(body: dict, *, code: str, message_contains: str) -> None:
    """Check the standard ``{"error": {...}}`` envelope."""
    assert "error" in body
    err = body["error"]
    assert err["code"] == code
    assert message_contains in err["message"]
    assert "correlation_id" in err
    assert isinstance(err["details"], dict)


# ---------------------------------------------------------------------------
# Tests: each exception type -> correct HTTP status
# ---------------------------------------------------------------------------
class TestEntityNotFoundError:
    def test_status_code(self, client: TestClient) -> None:
        resp = client.get("/raise-entity-not-found")
        assert resp.status_code == 404

    def test_error_envelope(self, client: TestClient) -> None:
        body = client.get("/raise-entity-not-found").json()
        _assert_error_envelope(body, code="ENTITY_NOT_FOUND", message_contains="not found")

    def test_details_propagated(self, client: TestClient) -> None:
        body = client.get("/raise-entity-not-found").json()
        assert body["error"]["details"]["entity_type"] == "Programme"


class TestValidationError:
    def test_status_code(self, client: TestClient) -> None:
        resp = client.get("/raise-validation")
        assert resp.status_code == 422

    def test_error_envelope(self, client: TestClient) -> None:
        body = client.get("/raise-validation").json()
        _assert_error_envelope(body, code="VALIDATION_ERROR", message_contains="empty")


class TestBusinessRuleViolationError:
    def test_status_code(self, client: TestClient) -> None:
        resp = client.get("/raise-business-rule")
        assert resp.status_code == 400

    def test_error_envelope(self, client: TestClient) -> None:
        body = client.get("/raise-business-rule").json()
        _assert_error_envelope(
            body,
            code="BUSINESS_RULE_VIOLATION",
            message_contains="Cannot start analysis",
        )


class TestConflictError:
    def test_status_code(self, client: TestClient) -> None:
        resp = client.get("/raise-conflict")
        assert resp.status_code == 409

    def test_error_envelope(self, client: TestClient) -> None:
        body = client.get("/raise-conflict").json()
        _assert_error_envelope(body, code="CONFLICT", message_contains="already exists")


class TestBaseDomainError:
    def test_status_code(self, client: TestClient) -> None:
        """Base ``DomainError`` without a specific subclass maps to 400."""
        resp = client.get("/raise-base-domain")
        assert resp.status_code == 400

    def test_error_envelope(self, client: TestClient) -> None:
        body = client.get("/raise-base-domain").json()
        _assert_error_envelope(body, code="DOMAIN_ERROR", message_contains="Generic")


class TestUnhandledException:
    def test_returns_500(self, client: TestClient) -> None:
        resp = client.get("/raise-unhandled")
        assert resp.status_code == 500

    def test_sanitized_response(self, client: TestClient) -> None:
        """Internal details must NOT leak to the client."""
        body = client.get("/raise-unhandled").json()
        _assert_error_envelope(
            body,
            code="INTERNAL_ERROR",
            message_contains="unexpected error",
        )
        # The actual RuntimeError message should not appear anywhere.
        assert "something broke" not in str(body)

    def test_error_envelope_structure(self, client: TestClient) -> None:
        body = client.get("/raise-unhandled").json()
        assert body["error"]["details"] == {}


class TestCorrelationIdInErrors:
    def test_correlation_id_propagated(self, client: TestClient) -> None:
        """The correlation ID from the request header appears in the error body."""
        custom_id = "test-correlation-12345"
        resp = client.get(
            "/raise-entity-not-found",
            headers={"X-Request-ID": custom_id},
        )
        body = resp.json()
        assert body["error"]["correlation_id"] == custom_id

    def test_generated_correlation_id_present(self, client: TestClient) -> None:
        """When no X-Request-ID is sent, a generated UUID still appears."""
        resp = client.get("/raise-entity-not-found")
        body = resp.json()
        assert body["error"]["correlation_id"] != ""
        assert len(body["error"]["correlation_id"]) > 0

    def test_correlation_id_in_response_header(self, client: TestClient) -> None:
        custom_id = "header-check-id"
        resp = client.get(
            "/raise-validation",
            headers={"X-Request-ID": custom_id},
        )
        assert resp.headers.get("x-request-id") == custom_id
