import uuid
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status

from middleware.auth import require_auth
from schemas.auth import RequestContext, UserRole


async def resolve_tenant_id(
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_auth)],
    x_tenant_id: str | None = Cookie(None, alias="tenant_id"),
) -> uuid.UUID:
    if ctx.role == UserRole.ADMIN:
        if ctx.tenant_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not assigned to token")
        return uuid.UUID(ctx.tenant_id)

    if x_tenant_id is None:
        if "text/html" in request.headers.get("accept", ""):
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                headers={"Location": "/select-tenant"}
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant selection required. Please select a tenant first.",
        )
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant_id format")

