from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import require_system_admin, require_admin
from middleware.tenant import resolve_tenant_id
from schemas.auth import RequestContext
from workers.tasks import refresh_dashboard_aggregates

from schemas.mapping import MappingFilterParams, MappingListResponse, RemapRequest, RemapResponse, BulkRemapRequest, BulkRemapResponse
from services.mapping_service import list_mappings, remap_doctor, bulk_remap_doctors, get_all_doctor_ids, get_filter_options
from models.auth import User
from sqlalchemy import select

router = APIRouter(prefix="/api/internal", tags=["internal"])


@router.post("/refresh-dashboard")
async def trigger_refresh(
    ctx: Annotated[RequestContext, Depends(require_system_admin)],
):
    refresh_dashboard_aggregates.apply_async(queue="analytics-refresh")
    return {"status": "queued"}


@router.get(
    "/mappings",
    response_model=MappingListResponse,
    summary="List doctor–MR mappings with filters and pagination",
)
async def get_doctor_mr_mappings(
    doctor_name: str | None = None,
    mr_name: str | None = None,
    manager_name: str | None = None,
    geolocation: str | None = None,
    page: int = 1,
    page_size: int = 15,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
    tenant_id: str = Depends(resolve_tenant_id),
):
    filters = MappingFilterParams(
        doctor_name=doctor_name,
        mr_name=mr_name,
        manager_name=manager_name,
        geolocation=geolocation,
        page=page,
        page_size=page_size,
    )
    return await list_mappings(db, tenant_id, filters)


@router.patch(
    "/mappings/{doctor_id}/remap",
    response_model=RemapResponse,
    summary="Remap a doctor to a different MR",
)
async def remap_doctor_mr(
    doctor_id: str,
    payload: RemapRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
    tenant_id: str = Depends(resolve_tenant_id),
):
    return await remap_doctor(db, tenant_id, doctor_id, payload)


@router.patch(
    "/mappings/bulk-remap",
    response_model=BulkRemapResponse,
    summary="Bulk remap multiple doctors to a single MR",
)
async def bulk_remap_doctor_mr(
    payload: BulkRemapRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
    tenant_id: str = Depends(resolve_tenant_id),
):
    return await bulk_remap_doctors(db, tenant_id, payload)


@router.get(
    "/mappings/filter-options",
    summary="Get distinct filter options for mappings dropdowns"
)
async def get_mappings_filter_options(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
    tenant_id: str = Depends(resolve_tenant_id),
):
    return await get_filter_options(db, tenant_id)


@router.get(
    "/mappings/doctor-ids",
    summary="Get all doctor IDs matching filters (for Select All across pages)",
)
async def get_all_doctor_ids_endpoint(
    doctor_name: str | None = None,
    mr_name: str | None = None,
    manager_name: str | None = None,
    geolocation: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
    tenant_id: str = Depends(resolve_tenant_id),
):
    filters = MappingFilterParams(
        doctor_name=doctor_name,
        mr_name=mr_name,
        manager_name=manager_name,
        geolocation=geolocation,
    )
    ids = await get_all_doctor_ids(db, tenant_id, filters)
    return {"doctor_ids": ids, "total": len(ids)}


@router.get(
    "/mrs",
    summary="Get list of MRs for dropdown",
)
async def get_tenant_mrs(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
    tenant_id: str = Depends(resolve_tenant_id),
):
    query = select(User).where(User.tenant_id == tenant_id, User.role == "MR")
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [
        {
            "mr_user_id": str(u.id),
            "mr_name": u.full_name,
        }
        for u in users
    ]
