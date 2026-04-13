import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import require_auth
from middleware.tenant import resolve_tenant_id
from schemas.auth import RequestContext
from schemas.dashboard import DashboardFilters
from services.dashboard_service import DashboardService

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_auth)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    geography: str | None = Query(None),
    form_status: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    svc = DashboardService(db)
    filters = DashboardFilters(geography=geography, form_status=form_status, page=page)
    summary = await svc.get_summary(tenant_id)
    listing = await svc.get_list(tenant_id, filters)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "ctx": ctx,
            "summary": summary,
            "listing": listing,
            "filters": filters,
        },
    )


@router.get("/submission/{submission_id}", response_class=HTMLResponse)
async def submission_page(
    request: Request,
    submission_id: uuid.UUID,
    ctx: Annotated[RequestContext, Depends(require_auth)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from services.submission_service import SubmissionService

    detail = await SubmissionService(db).get_submission(submission_id, tenant_id)
    return templates.TemplateResponse(
        "submission.html",
        {"request": request, "ctx": ctx, "detail": detail},
    )
