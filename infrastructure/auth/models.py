"""Auth data models — user context, token payload, and roles."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    """Platform roles for RBAC."""

    ADMIN = "admin"
    PROGRAMME_MANAGER = "programme_manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"


@dataclass(frozen=True)
class CurrentUser:
    """Authenticated user context extracted from JWT."""

    id: str
    email: str
    roles: tuple[Role, ...]
    customer_id: str

    def has_role(self, role: Role) -> bool:
        return role in self.roles

    def has_any_role(self, *roles: Role) -> bool:
        return any(r in self.roles for r in roles)


@dataclass(frozen=True)
class TokenPayload:
    """Decoded JWT payload."""

    sub: str
    email: str
    roles: list[str]
    customer_id: str
    exp: int
    iat: int


# Default dev user injected when auth is disabled
DEV_USER = CurrentUser(
    id="dev-user",
    email="dev@hanaforge.local",
    roles=(Role.ADMIN,),
    customer_id="dev-tenant",
)
