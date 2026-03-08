"""Authentication middleware — Bearer token extraction and user context.

TODO: Integrate Firebase Auth for production token verification.
TODO: Add tenant isolation checks against the token claims.
TODO: Cache verified tokens with short TTL to reduce auth latency.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict[str, str]:
    """Extract and validate the Bearer token from the Authorization header.

    For development: accepts any non-empty token and returns a stub user context.
    For production: this should verify the token against Firebase Auth and extract
    real user_id / tenant_id from the JWT claims.
    """
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # TODO: Replace with Firebase Auth token verification:
    #   decoded = firebase_admin.auth.verify_id_token(token)
    #   user_id = decoded["uid"]
    #   tenant_id = decoded.get("tenant_id", "default")

    return {
        "user_id": "dev-user",
        "tenant_id": "dev-tenant",
        "token": token,
    }
