from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import require_admin
from middleware.tenant import resolve_tenant_id
from schemas.auth import RequestContext
from services.form_service import FormService
import uuid

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="templates")


@router.get("/form-management", response_class=HTMLResponse)
async def form_management_list(
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
):
    if ctx.role != "SYSTEM_ADMIN":
        return HTMLResponse(content="Forbidden: System Admin only", status_code=403)

    return templates.TemplateResponse(
        "form_management.html",
        {"request": request, "ctx": ctx},
    )


@router.get("/form-management/{form_id}", response_class=HTMLResponse)
async def form_management_detail(
    request: Request,
    form_id: str,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if ctx.role != "SYSTEM_ADMIN":
        return HTMLResponse(content="Forbidden: System Admin only", status_code=403)

    draft_id = ""
    service = FormService(db)
    draft = await service.get_latest_draft_version(form_id, tenant_id)
    if draft:
        draft_id = str(draft.id)

    return templates.TemplateResponse(
        "form_builder.html",
        {"request": request, "ctx": ctx, "form_id": form_id, "draft_id": draft_id},
    )
