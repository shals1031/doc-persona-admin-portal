from enum import StrEnum

from pydantic import BaseModel


class UserRole(StrEnum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    CUSTOMER_ADMIN = "CUSTOMER_ADMIN"


class TokenPayload(BaseModel):
    sub: str           # user identifier
    role: UserRole
    tenant_id: str | None = None
    exp: int | None = None


class RequestContext(BaseModel):
    user_id: str
    role: UserRole
    tenant_id: str | None
