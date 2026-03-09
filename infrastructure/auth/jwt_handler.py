"""JWT token creation and verification."""

from __future__ import annotations

import time
from typing import Any

import jwt

from infrastructure.auth.models import CurrentUser, Role, TokenPayload


class JWTHandler:
    """Creates and verifies JWT tokens for HanaForge authentication."""

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        expiry_seconds: int = 3600,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._expiry_seconds = expiry_seconds

    def create_token(
        self,
        user_id: str,
        email: str,
        roles: list[str],
        customer_id: str,
    ) -> str:
        """Create a signed JWT token."""
        now = int(time.time())
        payload: dict[str, Any] = {
            "sub": user_id,
            "email": email,
            "roles": roles,
            "customer_id": customer_id,
            "iat": now,
            "exp": now + self._expiry_seconds,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode a JWT token. Raises jwt.PyJWTError on failure."""
        data = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        return TokenPayload(
            sub=data["sub"],
            email=data["email"],
            roles=data["roles"],
            customer_id=data["customer_id"],
            exp=data["exp"],
            iat=data["iat"],
        )

    def token_to_user(self, token: str) -> CurrentUser:
        """Verify token and return a CurrentUser."""
        payload = self.verify_token(token)
        return CurrentUser(
            id=payload.sub,
            email=payload.email,
            roles=tuple(Role(r) for r in payload.roles),
            customer_id=payload.customer_id,
        )
