import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.dashboard import DashboardFact
from core.config import settings
from schemas.dashboard import DashboardFilters


class DashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(self, tenant_id: uuid.UUID) -> dict[str, int]:
        result = await self.db.execute(
            select(
                func.count().filter(func.lower(DashboardFact.form_status) == "draft").label("draft"),
                func.count().filter(func.lower(DashboardFact.form_status) == "submitted").label("submitted"),
                func.count().filter(func.lower(DashboardFact.form_status) == "approved").label("approved"),
                func.count().filter(func.lower(DashboardFact.form_status) == "rejected").label("rejected"),
            ).where(DashboardFact.tenant_id == tenant_id)
        )
        row = result.one()
        return {"draft": row.draft, "submitted": row.submitted, "approved": row.approved, "rejected": row.rejected}

    async def get_list(self, tenant_id: uuid.UUID, filters: DashboardFilters) -> tuple[list[DashboardFact], int]:
        query = select(DashboardFact).where(DashboardFact.tenant_id == tenant_id)

        if filters.geography:
            query = query.where(DashboardFact.geography.ilike(f"%{filters.geography}%"))
        if filters.mr_name:
            query = query.where(DashboardFact.mr_name.ilike(f"%{filters.mr_name}%"))
        if filters.mr_manager_name:
            query = query.where(DashboardFact.mr_manager_name.ilike(f"%{filters.mr_manager_name}%"))
        if filters.doctor_name:
            query = query.where(DashboardFact.doctor_name.ilike(f"%{filters.doctor_name}%"))
        if filters.form_status:
            query = query.where(func.lower(DashboardFact.form_status) == filters.form_status.lower())
        if filters.specialty:
            query = query.where(DashboardFact.specialty == filters.specialty)
        if filters.tier:
            query = query.where(DashboardFact.tier == filters.tier)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        sort_col = getattr(DashboardFact, filters.sort_by, DashboardFact.created_at)
        if filters.sort_order == "desc":
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())

        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)

        result = await self.db.execute(query)
        return result.scalars().all(), total

    async def get_all_for_export(self, tenant_id: uuid.UUID, filters: DashboardFilters) -> list[DashboardFact]:
        query = select(DashboardFact).where(DashboardFact.tenant_id == tenant_id)

        if filters.geography:
            query = query.where(DashboardFact.geography.ilike(f"%{filters.geography}%"))
        if filters.mr_name:
            query = query.where(DashboardFact.mr_name.ilike(f"%{filters.mr_name}%"))
        if filters.mr_manager_name:
            query = query.where(DashboardFact.mr_manager_name.ilike(f"%{filters.mr_manager_name}%"))
        if filters.doctor_name:
            query = query.where(DashboardFact.doctor_name.ilike(f"%{filters.doctor_name}%"))
        if filters.form_status:
            query = query.where(func.lower(DashboardFact.form_status) == filters.form_status.lower())
        if filters.specialty:
            query = query.where(DashboardFact.specialty == filters.specialty)
        if filters.tier:
            query = query.where(DashboardFact.tier == filters.tier)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def refresh_aggregates(self) -> None:
        schema = settings.database_schema
        await self.db.execute(
            text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {schema}.dashboard_fact")
        )
        await self.db.execute(
            text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {schema}.doctor_profile_flat_table")
        )
        await self.db.execute(
            text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {schema}.dashboard_aggregates")
        )
        await self.db.commit()
