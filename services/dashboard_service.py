import io
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_client import cache_get, cache_set, publish_event
from repositories.dashboard_repository import DashboardRepository
from schemas.dashboard import DashboardFilters, DashboardListResponse, DashboardSummary


_SUMMARY_TTL = 120   # 2 minutes
_LIST_TTL = 60       # 1 minute


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.repo = DashboardRepository(db)

    async def get_summary(self, tenant_id: uuid.UUID) -> DashboardSummary:
        cache_key = f"dashboard:summary:{tenant_id}"
        cached = await cache_get(cache_key)
        if cached:
            return DashboardSummary(**cached)

        data = await self.repo.get_summary(tenant_id)
        await cache_set(cache_key, data, ttl_seconds=_SUMMARY_TTL)
        return DashboardSummary(**data)

    async def get_list(self, tenant_id: uuid.UUID, filters: DashboardFilters) -> DashboardListResponse:
        cache_key = f"dashboard:list:{tenant_id}:{filters.model_dump_json()}"
        cached = await cache_get(cache_key)
        if cached:
            return DashboardListResponse(**cached)

        items, total = await self.repo.get_list(tenant_id, filters)
        response = DashboardListResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )
        await cache_set(cache_key, response.model_dump(), ttl_seconds=_LIST_TTL)
        return response

    async def export_excel(self, tenant_id: uuid.UUID, filters: DashboardFilters) -> bytes:
        from openpyxl import Workbook

        rows = await self.repo.get_all_for_export(tenant_id, filters)
        wb = Workbook()
        ws = wb.active
        ws.title = "Dashboard Export"

        headers = [
            "Submission ID", "MR Name", "MR Manager", "Geography",
            "Doctor Name", "Specialty", "Tier", "Form Status", "Created At",
        ]
        ws.append(headers)

        for row in rows:
            ws.append([
                str(row.submission_id) if row.submission_id else "",
                row.mr_name or "",
                row.mr_manager_name or "",
                row.geography or "",
                row.doctor_name or "",
                row.specialty or "",
                row.tier or "",
                row.form_status or "",
                str(row.created_at) if row.created_at else "",
            ])

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    async def trigger_aggregate_refresh(self) -> None:
        await publish_event("analytics:refresh", {"action": "refresh_aggregates"})
