from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.auth import LoginRequest, TokenResponse
from services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    login_data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AuthService(db)
    result = await svc.authenticate_user(login_data)
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result["error"],
        )

    # Set cookie for web routes
    response.set_cookie(
        key="access_token",
        value=result["access_token"],
        httponly=True,
        max_age=1800, # 30 minutes
        samesite="lax",
        path="/"
    )
    
    return {
        "access_token": result["access_token"],
        "token_type": "bearer",
        "role": result["role"]
    }
