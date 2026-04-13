from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.config import settings
from schemas.auth import RequestContext, TokenPayload, UserRole

_bearer = HTTPBearer()


def _decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenPayload(**payload)
    except (JWTError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_auth(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> RequestContext:
    payload = _decode_token(credentials.credentials)
    return RequestContext(
        user_id=payload.sub,
        role=payload.role,
        tenant_id=payload.tenant_id,
    )


async def require_system_admin(
    ctx: Annotated[RequestContext, Depends(require_auth)],
) -> RequestContext:
    if ctx.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System admin access required")
    return ctx
