"""Tests for authentication infrastructure — JWT handling and middleware."""

from __future__ import annotations

import jwt as pyjwt
import pytest

from infrastructure.auth.jwt_handler import JWTHandler
from infrastructure.auth.models import DEV_USER, CurrentUser, Role

SECRET = "test-secret-key"
ALGORITHM = "HS256"


@pytest.fixture
def handler() -> JWTHandler:
    return JWTHandler(secret=SECRET, algorithm=ALGORITHM, expiry_seconds=3600)


class TestJWTHandler:
    def test_create_and_verify_token(self, handler: JWTHandler) -> None:
        token = handler.create_token(
            user_id="u1",
            email="test@example.com",
            roles=["admin", "developer"],
            customer_id="c1",
        )
        payload = handler.verify_token(token)
        assert payload.sub == "u1"
        assert payload.email == "test@example.com"
        assert payload.roles == ["admin", "developer"]
        assert payload.customer_id == "c1"

    def test_token_to_user(self, handler: JWTHandler) -> None:
        token = handler.create_token(
            user_id="u1",
            email="test@example.com",
            roles=["admin"],
            customer_id="c1",
        )
        user = handler.token_to_user(token)
        assert isinstance(user, CurrentUser)
        assert user.id == "u1"
        assert user.email == "test@example.com"
        assert user.roles == (Role.ADMIN,)
        assert user.customer_id == "c1"

    def test_expired_token_rejected(self) -> None:
        handler = JWTHandler(secret=SECRET, algorithm=ALGORITHM, expiry_seconds=-1)
        token = handler.create_token(
            user_id="u1",
            email="test@example.com",
            roles=["viewer"],
            customer_id="c1",
        )
        with pytest.raises(pyjwt.ExpiredSignatureError):
            handler.verify_token(token)

    def test_invalid_token_rejected(self, handler: JWTHandler) -> None:
        with pytest.raises(pyjwt.DecodeError):
            handler.verify_token("not-a-real-token")

    def test_wrong_secret_rejected(self, handler: JWTHandler) -> None:
        token = handler.create_token(
            user_id="u1",
            email="test@example.com",
            roles=["admin"],
            customer_id="c1",
        )
        other_handler = JWTHandler(secret="wrong-secret", algorithm=ALGORITHM)
        with pytest.raises(pyjwt.InvalidSignatureError):
            other_handler.verify_token(token)


class TestCurrentUser:
    def test_has_role(self) -> None:
        user = CurrentUser(
            id="u1",
            email="a@b.com",
            roles=(Role.ADMIN, Role.DEVELOPER),
            customer_id="c1",
        )
        assert user.has_role(Role.ADMIN)
        assert not user.has_role(Role.VIEWER)

    def test_has_any_role(self) -> None:
        user = CurrentUser(
            id="u1",
            email="a@b.com",
            roles=(Role.VIEWER,),
            customer_id="c1",
        )
        assert user.has_any_role(Role.ADMIN, Role.VIEWER)
        assert not user.has_any_role(Role.ADMIN, Role.DEVELOPER)

    def test_dev_user_is_admin(self) -> None:
        assert DEV_USER.has_role(Role.ADMIN)
        assert DEV_USER.id == "dev-user"
