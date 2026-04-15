import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import require_auth
from middleware.tenant import resolve_tenant_id
from schemas.auth import RequestContext
from schemas.dashboard import DashboardFilters, DashboardListResponse, DashboardSummary
from services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    ctx: Annotated[RequestContext, Depends(require_auth)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await DashboardService(db).get_summary(tenant_id)


@router.get("/list", response_model=DashboardListResponse)
async def get_list(
    ctx: Annotated[RequestContext, Depends(require_auth)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    geography: str | None = Query(None),
    mr_name: str | None = Query(None),
    mr_manager_name: str | None = Query(None),
    doctor_name: str | None = Query(None),
    form_status: str | None = Query(None),
    specialty: str | None = Query(None),
    tier: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
):
    filters = DashboardFilters(
        geography=geography,
        mr_name=mr_name,
        mr_manager_name=mr_manager_name,
        doctor_name=doctor_name,
        form_status=form_status,
        specialty=specialty,
        tier=tier,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await DashboardService(db).get_list(tenant_id, filters)


@router.get("/export")
async def export_dashboard(
    ctx: Annotated[RequestContext, Depends(require_auth)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    geography: str | None = Query(None),
    mr_name: str | None = Query(None),
    mr_manager_name: str | None = Query(None),
    doctor_name: str | None = Query(None),
    form_status: str | None = Query(None),
):
    filters = DashboardFilters(
        geography=geography,
        mr_name=mr_name,
        mr_manager_name=mr_manager_name,
        doctor_name=doctor_name,
        form_status=form_status
    )
    data = await DashboardService(db).export_excel(tenant_id, filters)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=dashboard_export.xlsx"},
    )
