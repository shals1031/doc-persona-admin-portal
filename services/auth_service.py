import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from repositories.user_repository import UserRepository
from schemas.auth import LoginRequest, TokenPayload, UserRole


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    @staticmethod
    def get_password_hash(password: str) -> str:
        # bcrypt expects bytes
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        return encoded_jwt

    async def authenticate_user(self, login_data: LoginRequest) -> dict[str, Any] | None:
        user = await self.repo.get_by_username(login_data.username)
        if not user:
            return None
        if not self.verify_password(login_data.password, user.password_hash):
            return None
        
        # Only SYSTEM_ADMIN and ADMIN can log in (as per requirements)
        if user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN]:
            return {"error": "Insufficient permissions"}

        token_data = {
            "sub": str(user.id),
            "role": user.role,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "full_name": user.full_name,
        }
        access_token = self.create_access_token(token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": user.role,
            "user_id": str(user.id)
        }
