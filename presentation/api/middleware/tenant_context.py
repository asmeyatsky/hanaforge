"""Tenant context middleware — extracts tenant (customer) identity for multi-tenancy.

When auth is enabled, the customer_id is extracted from the authenticated
user's JWT claims.  When auth is disabled (dev mode), a default dev tenant
is returned so that all queries still filter by tenant.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends

from infrastructure.auth.models import CurrentUser
from presentation.api.middleware.auth import get_current_user


@dataclass(frozen=True)
class TenantContext:
    """Immutable tenant identity extracted from the current request."""

    customer_id: str


async def get_tenant_context(
    user: CurrentUser = Depends(get_current_user),
) -> TenantContext:
    """FastAPI dependency that resolves the tenant for the current request.

    * Auth enabled  -> customer_id comes from the JWT-backed CurrentUser.
    * Auth disabled -> falls through to the DEV_USER whose customer_id is
      ``"dev-tenant"``.
    """
    return TenantContext(customer_id=user.customer_id)
