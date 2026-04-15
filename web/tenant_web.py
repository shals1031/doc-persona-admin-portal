from typing import Annotated
from fastapi import APIRouter, Depends, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from middleware.auth import require_auth, require_system_admin
from models.control import Tenant
from schemas.auth import RequestContext

router = APIRouter(tags=["web-tenant"])
templates = Jinja2Templates(directory="templates")

@router.get("/select-tenant", response_class=HTMLResponse)
async def select_tenant_page(
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_system_admin)],
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Tenant).where(Tenant.is_active == True))
    tenants = result.scalars().all()
    return templates.TemplateResponse("select_tenant.html", {"request": request, "tenants": tenants, "ctx": ctx})

@router.post("/select-tenant")
async def select_tenant(
    tenant_id: str = Form(...)
):
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="tenant_id", value=tenant_id, httponly=True, samesite="lax")
    return response

