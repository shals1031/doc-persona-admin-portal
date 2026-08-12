import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import require_admin, require_auth
from middleware.tenant import resolve_tenant_id
from schemas.auth import RequestContext
from schemas.dashboard import DashboardFilters
from services.campaign_service import CampaignService
from services.dashboard_service import DashboardService
from services.overview_service import OverviewService

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="templates")


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    """Parse an optional UUID query param, treating empty/blank as None.

    The dashboard filter dropdowns submit an empty string when 'All Regions' /
    'All Personas' is selected, which is not a valid UUID. Coerce those to None.
    """
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return uuid.UUID(value)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    region_id: str | None = Query(None),
    persona_id: str | None = Query(None),
):
    region_id = _parse_uuid(region_id)
    persona_id = _parse_uuid(persona_id)
    svc = OverviewService(db)
    overview = await svc.get_overview(tenant_id, region_id, persona_id)
    regions = await svc.get_regions(tenant_id)
    personas = await svc.get_personas(tenant_id)
    return templates.TemplateResponse(
        "overview.html",
        {
            "request": request,
            "ctx": ctx,
            "overview": overview,
            "regions": regions,
            "personas": personas,
            "filters": {
                "region_id": str(region_id) if region_id else "",
                "persona_id": str(persona_id) if persona_id else "",
            },
        },
    )


@router.get("/forms", response_class=HTMLResponse)
async def forms_page(
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    geography: str | None = Query(None),
    mr_name: str | None = Query(None),
    mr_manager_name: str | None = Query(None),
    doctor_name: str | None = Query(None),
    form_status: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    svc = DashboardService(db)
    filters = DashboardFilters(
        geography=geography,
        mr_name=mr_name,
        mr_manager_name=mr_manager_name,
        doctor_name=doctor_name,
        form_status=form_status,
        page=page
    )
    summary = await svc.get_summary(tenant_id)
    listing = await svc.get_list(tenant_id, filters)

    return templates.TemplateResponse(
        "forms.html",
        {
            "request": request,
            "ctx": ctx,
            "summary": summary,
            "listing": listing,
            "filters": filters,
        },
    )


@router.get("/campaigns", response_class=HTMLResponse)
async def campaigns_page(
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    brand_name: str | None = Query(None),
    material_type: str | None = Query(None),
    status: str | None = Query(None),
):
    page = await CampaignService(db).get_page(
        tenant_id,
        brand_name=brand_name,
        material_type=material_type,
        status=status,
    )
    return templates.TemplateResponse(
        "campaigns.html",
        {"request": request, "ctx": ctx, "page": page},
    )


@router.get("/persona-mix", response_class=HTMLResponse)
async def persona_mix_page(
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    region_id: str | None = Query(None),
    persona_id: str | None = Query(None),
):
    region_id = _parse_uuid(region_id)
    persona_id = _parse_uuid(persona_id)
    strategy = await OverviewService(db).get_persona_strategy(tenant_id, region_id, persona_id)
    return templates.TemplateResponse(
        "persona_mix.html",
        {"request": request, "ctx": ctx, "strategy": strategy},
    )


# Map common file extensions to a MIME type for the download response.
_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


@router.post("/campaigns/upload")
async def campaigns_upload(
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    brand_name: Annotated[str, Form()] = "",
    persona_name: Annotated[str, Form()] = "",
    material_type: Annotated[str, Form()] = "",
    file: Annotated[UploadFile | None, File()] = None,
):
    file_name = None
    file_data = None
    file_size = None
    if file is not None and file.filename:
        file_data = await file.read()
        file_size = len(file_data)
        file_name = file.filename

    try:
        uploaded_by = uuid.UUID(str(ctx.user_id)) if ctx.user_id else None
    except (ValueError, TypeError):
        uploaded_by = None

    await CampaignService(db).create_material(
        tenant_id=tenant_id,
        uploaded_by=uploaded_by,
        brand_name=brand_name or None,
        persona_name=persona_name or None,
        material_type=material_type or None,
        file_name=file_name,
        file_data=file_data,
        file_size_bytes=file_size,
    )
    return RedirectResponse(url="/campaigns", status_code=303)


@router.get("/campaigns/{material_id}/download")
async def campaigns_download(
    material_id: uuid.UUID,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await CampaignService(db).get_material_file(tenant_id, material_id)
    if result is None or result[1] is None:
        raise HTTPException(status_code=404, detail="File not found")
    file_name, file_data = result
    ext = (file_name or "").rsplit(".", 1)[-1].lower() if file_name and "." in file_name else ""
    media_type = _CONTENT_TYPES.get(ext, "application/octet-stream")
    return Response(
        content=file_data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file_name or "download"}"'
        },
    )


@router.post("/campaigns/{material_id}/push")
async def campaigns_push(
    material_id: uuid.UUID,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await CampaignService(db).set_status(tenant_id, material_id, "pushed")
    return RedirectResponse(url="/campaigns", status_code=303)


@router.post("/campaigns/{material_id}/recall")
async def campaigns_recall(
    material_id: uuid.UUID,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await CampaignService(db).set_status(tenant_id, material_id, "recalled")
    return RedirectResponse(url="/campaigns", status_code=303)


@router.get("/submission/{submission_id}", response_class=HTMLResponse)
async def submission_page(
    request: Request,
    submission_id: uuid.UUID,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from services.submission_service import SubmissionService

    detail = await SubmissionService(db).get_submission(submission_id, tenant_id)
    return templates.TemplateResponse(
        "submission.html",
        {"request": request, "ctx": ctx, "detail": detail},
    )


@router.get("/doctor-mr-mapping")
async def doctor_mr_mapping_page(
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_admin)],
    tenant_id: Annotated[uuid.UUID, Depends(resolve_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    overview = await OverviewService(db).get_overview(tenant_id)
    stats = {
        "total": overview["total_doctors"],
        "mapped": overview["mapped"],
        "unmapped": overview["unmapped"],
    }
    return templates.TemplateResponse(
        "doctor_mr_mapping.html",
        {"request": request, "ctx": ctx, "stats": stats},
    )
