from enum import StrEnum
from pydantic import BaseModel

class UserRole(StrEnum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    ADMIN = "ADMIN"

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: UserRole

class TokenPayload(BaseModel):
    sub: str  # user identifier
    role: UserRole
    tenant_id: str | None = None
    full_name: str | None = None
    exp: int | None = None

class RequestContext(BaseModel):
    user_id: str
    role: UserRole
    tenant_id: str | None
    full_name: str | None

