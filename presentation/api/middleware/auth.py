"""Authentication middleware — JWT verification with dev-mode bypass.

When auth is disabled (default for dev), a default admin user is injected.
When enabled, full JWT validation runs with role-based access control.
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from infrastructure.auth.models import DEV_USER, CurrentUser, Role

_bearer_scheme = HTTPBearer(auto_error=False)


def _get_jwt_handler(request: Request) -> Any:
    """Retrieve the JWTHandler from the DI container."""
    return request.app.state.container.resolve("JWTHandler")


def _is_auth_enabled(request: Request) -> bool:
    """Check if authentication is enabled in settings."""
    settings = request.app.state.container.resolve("Settings")
    return getattr(settings, "auth_enabled", False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    """Extract and validate the Bearer token, or return dev user if auth is disabled."""
    if not _is_auth_enabled(request):
        return DEV_USER

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwt_handler = _get_jwt_handler(request)
    try:
        return cast(CurrentUser, jwt_handler.token_to_user(credentials.credentials))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(*required_roles: Role):
    """Dependency factory that checks the user has at least one of the required roles."""

    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has_any_role(*required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in required_roles]}",
            )
        return user

    return _check


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser | None:
    """Return user if token present, None otherwise. Never raises 401."""
    if not _is_auth_enabled(request):
        return DEV_USER

    if credentials is None or not credentials.credentials:
        return None

    jwt_handler = _get_jwt_handler(request)
    try:
        return cast(CurrentUser, jwt_handler.token_to_user(credentials.credentials))
    except Exception:
        return None
