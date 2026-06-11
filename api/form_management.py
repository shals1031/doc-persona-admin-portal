from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import require_admin
from middleware.tenant import resolve_tenant_id
import uuid
from schemas.auth import RequestContext
from schemas.form import (
    CreateFormRequest,
    CreateFormVersionRequest,
    PublishFormVersionRequest,
    UpdateFormRequest,
    UpdateSchemaRequest,
)
from services.form_service import FormService

router = APIRouter(prefix="/api/forms", tags=["forms"])


# ─── Form CRUD ────────────────────────────────────────────────────────


@router.post("")
async def create_form(
    data: CreateFormRequest,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = FormService(db)
    return await service.create_form(data, ctx.user_id, ctx.role, str(tenant_id))


@router.get("")
async def get_forms(
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = FormService(db)
    forms = await service.get_all_forms(tenant_id)
    return {"data": forms, "meta": {"total": len(forms), "page": 1, "limit": 20}}


@router.get("/{form_id}")
async def get_form(
    form_id: str,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = FormService(db)
    return await service.get_form_with_current_version(form_id, tenant_id)


@router.patch("/{form_id}")
async def update_form(
    form_id: str,
    data: UpdateFormRequest,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = FormService(db)
    return await service.update_form(form_id, data, ctx.role, tenant_id)


@router.delete("/{form_id}")
async def remove_form(
    form_id: str,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = FormService(db)
    await service.remove_form(form_id, ctx.role, tenant_id)
    return {"message": "Form successfully deactivated"}


# ─── Version Management ───────────────────────────────────────────────


@router.get("/{form_id}/versions")
async def get_versions(
    form_id: str,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = FormService(db)
    return await service.get_versions(form_id, tenant_id)


@router.get("/{form_id}/versions/{version_id}")
async def get_version(
    form_id: str,
    version_id: str,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = FormService(db)
    return await service.get_version(form_id, version_id, tenant_id)


@router.post("/{form_id}/versions")
async def create_version(
    form_id: str,
    data: CreateFormVersionRequest,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = FormService(db)
    return await service.create_version(form_id, data, ctx.user_id, ctx.role, tenant_id)


@router.put("/{form_id}/versions/{version_id}/publish")
async def publish_version(
    form_id: str,
    version_id: str,
    data: PublishFormVersionRequest,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = FormService(db)
    return await service.publish_version(form_id, version_id, data, ctx.user_id, ctx.role, tenant_id)


@router.put("/{form_id}/versions/{version_id}/schema")
async def update_version_schema(
    form_id: str,
    version_id: str,
    data: UpdateSchemaRequest,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = FormService(db)
    return await service.update_version_schema(form_id, version_id, data, ctx.user_id, ctx.role, tenant_id)



