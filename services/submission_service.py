import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.submission_repository import SubmissionRepository
from schemas.submission import SubmissionWithAiProfile


class SubmissionService:
    def __init__(self, db: AsyncSession):
        self.repo = SubmissionRepository(db)

    async def get_submission(self, submission_id: uuid.UUID, tenant_id: uuid.UUID) -> SubmissionWithAiProfile:
        submission = await self.repo.get_by_id(submission_id, tenant_id)
        if submission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

        ai_profile = await self.repo.get_ai_profile(submission_id)

        return SubmissionWithAiProfile(submission=submission, ai_profile=ai_profile)
