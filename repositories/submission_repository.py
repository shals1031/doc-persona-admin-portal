import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.doctor import DoctorAiProfile, DoctorProfileFlatTable


class SubmissionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, submission_id: uuid.UUID, tenant_id: uuid.UUID) -> DoctorProfileFlatTable | None:
        # Verify tenant ownership via DoctorProfileFlatTable.tenant_id
        result = await self.db.execute(
            select(DoctorProfileFlatTable).where(
                DoctorProfileFlatTable.submission_id == submission_id,
                DoctorProfileFlatTable.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def get_raw_submission(self, submission_id: uuid.UUID):
        result = await self.db.execute(
            text("SELECT submission_data, form_version_id FROM public.submissions WHERE id = :id"),
            {"id": submission_id}
        )
        return result.fetchone()

    async def get_form_schema(self, form_version_id: uuid.UUID):
        result = await self.db.execute(
            text("SELECT schema_json FROM public.form_versions WHERE id = :id"),
            {"id": form_version_id}
        )
        return result.scalar_one_or_none()

    async def get_ai_profile(self, submission_id: uuid.UUID) -> DoctorAiProfile | None:
        result = await self.db.execute(
            select(DoctorAiProfile).where(DoctorAiProfile.submission_id == submission_id)
        )
        return result.scalar_one_or_none()
