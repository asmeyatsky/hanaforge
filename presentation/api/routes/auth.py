"""Auth routes — login, token refresh, user info, and dev-token generation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from infrastructure.auth.models import CurrentUser
from presentation.api.middleware.auth import get_current_user

router = APIRouter(prefix="", tags=["Auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str
    password: str


class DevTokenRequest(BaseModel):
    user_id: str = "dev-user"
    email: str = "dev@hanaforge.local"
    roles: list[str] = ["admin"]
    customer_id: str = "dev-tenant"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    roles: list[str]
    customer_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive a JWT",
)
async def login(body: LoginRequest, request: Request) -> TokenResponse:
    """Authenticate with email/password. In dev mode, accepts any credentials."""
    settings = request.app.state.container.resolve("Settings")
    jwt_handler = request.app.state.container.resolve("JWTHandler")

    if getattr(settings, "auth_enabled", False):
        # Production: validate against identity provider
        # For now, reject — real IdP integration is a future task
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Production auth requires Identity Platform integration",
        )

    # Dev mode: accept any credentials, issue admin token
    token = jwt_handler.create_token(
        user_id="dev-user",
        email=body.email,
        roles=["admin"],
        customer_id="dev-tenant",
    )
    return TokenResponse(
        access_token=token,
        expires_in=getattr(settings, "jwt_expiry_minutes", 60) * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an existing JWT",
)
async def refresh_token(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> TokenResponse:
    """Issue a fresh token for an authenticated user."""
    settings = request.app.state.container.resolve("Settings")
    jwt_handler = request.app.state.container.resolve("JWTHandler")

    token = jwt_handler.create_token(
        user_id=user.id,
        email=user.email,
        roles=[r.value for r in user.roles],
        customer_id=user.customer_id,
    )
    return TokenResponse(
        access_token=token,
        expires_in=getattr(settings, "jwt_expiry_minutes", 60) * 60,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user info",
)
async def me(user: CurrentUser = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse(
        id=user.id,
        email=user.email,
        roles=[r.value for r in user.roles],
        customer_id=user.customer_id,
    )


@router.post(
    "/dev-token",
    response_model=TokenResponse,
    summary="Generate a dev token (dev mode only)",
)
async def dev_token(body: DevTokenRequest, request: Request) -> TokenResponse:
    """Generate a JWT with arbitrary claims. Only available when auth is disabled."""
    settings = request.app.state.container.resolve("Settings")

    if getattr(settings, "auth_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev token endpoint is disabled in production",
        )

    jwt_handler = request.app.state.container.resolve("JWTHandler")
    token = jwt_handler.create_token(
        user_id=body.user_id,
        email=body.email,
        roles=body.roles,
        customer_id=body.customer_id,
    )
    return TokenResponse(
        access_token=token,
        expires_in=getattr(settings, "jwt_expiry_minutes", 60) * 60,
    )
