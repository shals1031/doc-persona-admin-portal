from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.config import settings
from schemas.auth import RequestContext, TokenPayload, UserRole

_bearer = HTTPBearer(auto_error=False)


def _decode_token(token: str, request: Request | None = None) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenPayload(**payload)
    except (JWTError, Exception):
        if request and "text/html" in request.headers.get("accept", ""):
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                headers={"Location": "/login"}
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_auth(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> RequestContext:
    token = None
    if credentials:
        token = credentials.credentials
    else:
        # Fallback to cookie for web routes
        token = request.cookies.get("access_token")

    if not token:
        if "text/html" in request.headers.get("accept", ""):
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                headers={"Location": "/login"}
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_token(token, request)
    return RequestContext(
        user_id=payload.sub,
        role=payload.role,
        tenant_id=payload.tenant_id,
        full_name=payload.full_name,
    )


async def require_admin(
    ctx: Annotated[RequestContext, Depends(require_auth)],
) -> RequestContext:
    if ctx.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this page."
        )
    return ctx


async def require_system_admin(
    ctx: Annotated[RequestContext, Depends(require_auth)],
) -> RequestContext:
    if ctx.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System admin access required")
    return ctx
