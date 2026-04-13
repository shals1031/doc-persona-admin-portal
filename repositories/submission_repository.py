import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.doctor import DoctorAiProfile, DoctorProfileFlatTable


class SubmissionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, submission_id: uuid.UUID, tenant_id: uuid.UUID) -> DoctorProfileFlatTable | None:
        # Verify tenant ownership via tenant_mapping before returning
        from models.control import TenantMapping

        mapping = await self.db.execute(
            select(TenantMapping).where(
                TenantMapping.submission_id == submission_id,
                TenantMapping.tenant_id == tenant_id,
            )
        )
        if mapping.scalar_one_or_none() is None:
            return None

        result = await self.db.execute(
            select(DoctorProfileFlatTable).where(DoctorProfileFlatTable.submission_id == submission_id)
        )
        return result.scalar_one_or_none()

    async def get_ai_profile(self, submission_id: uuid.UUID) -> DoctorAiProfile | None:
        result = await self.db.execute(
            select(DoctorAiProfile).where(DoctorAiProfile.submission_id == submission_id)
        )
        return result.scalar_one_or_none()
