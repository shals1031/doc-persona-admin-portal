import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import require_auth
from middleware.tenant import resolve_tenant_id
from schemas.auth import RequestContext
from schemas.submission import SubmissionWithAiProfile
from services.submission_service import SubmissionService

router = APIRouter(prefix="/api/submission", tags=["submission"])


@router.get("/{submission_id}", response_model=SubmissionWithAiProfile)
async def get_submission(
    submission_id: uuid.UUID,
    ctx: Annotated[RequestContext, Depends(require_auth)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await SubmissionService(db).get_submission(submission_id, tenant_id)
