from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import require_system_admin
from schemas.auth import RequestContext
from services.dashboard_service import DashboardService
from workers.tasks import refresh_dashboard_aggregates

router = APIRouter(prefix="/api/internal", tags=["internal"])


@router.post("/refresh-dashboard")
async def trigger_refresh(
    ctx: Annotated[RequestContext, Depends(require_system_admin)],
):
    refresh_dashboard_aggregates.apply_async(queue="analytics-refresh")
    return {"status": "queued"}
