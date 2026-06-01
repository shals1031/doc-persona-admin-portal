from sqlalchemy.ext.asyncio import AsyncSession
from repositories.mapping_repo import (
    get_mappings_filtered,
    update_mapping_mr,
)
from schemas.mapping import (
    MappingFilterParams,
    MappingListResponse,
    DoctorMRMappingRead,
    RemapRequest,
    RemapResponse,
)
from fastapi import HTTPException
import math


async def list_mappings(
    db: AsyncSession,
    tenant_id: str,
    filters: MappingFilterParams,
) -> MappingListResponse:
    rows, total = await get_mappings_filtered(db, tenant_id, filters)
    total_pages = math.ceil(total / filters.page_size) if total > 0 else 1
    return MappingListResponse(
        items=[DoctorMRMappingRead(**r) for r in rows],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        total_pages=total_pages,
    )


async def remap_doctor(
    db: AsyncSession,
    tenant_id: str,
    doctor_id: str,
    payload: RemapRequest,
) -> RemapResponse:
    try:
        doc_name, new_mr_name, new_manager_name = await update_mapping_mr(
            db,
            tenant_id,
            doctor_id,
            new_mr_user_id=payload.new_mr_user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RemapResponse(
        doctor_id=doctor_id,
        doctor_name=doc_name,
        old_mr_name=None,  # We don't fetch old mr name in the optimized update
        new_mr_name=new_mr_name,
        message=f"{doc_name} successfully remapped to {new_mr_name}",
    )


async def get_filter_options(db: AsyncSession, tenant_id: str) -> dict:
    from repositories.mapping_repo import get_mapping_filter_options
    return await get_mapping_filter_options(db, tenant_id)
