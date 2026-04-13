import uuid
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

from middleware.auth import require_auth
from schemas.auth import RequestContext, UserRole


async def resolve_tenant_id(
    ctx: Annotated[RequestContext, Depends(require_auth)],
    x_tenant_id: str | None = Cookie(None, alias="tenant_id"),
) -> uuid.UUID:
    """
    SYSTEM_ADMIN: tenant_id must be set in cookie (mandatory tenant selection screen).
    CUSTOMER_ADMIN: tenant_id is taken directly from JWT — no override allowed.
    """
    if ctx.role == UserRole.CUSTOMER_ADMIN:
        if ctx.tenant_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not assigned to token")
        return uuid.UUID(ctx.tenant_id)

    # SYSTEM_ADMIN must have selected a tenant
    if x_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant selection required. Please select a tenant first.",
        )
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant_id format")
