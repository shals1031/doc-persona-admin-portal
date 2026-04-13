import uuid
from datetime import datetime

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    draft: int
    submitted: int
    approved: int
    rejected: int


class DashboardListItem(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    submission_id: uuid.UUID | None
    mr_name: str | None
    mr_manager_name: str | None
    geography: str | None
    doctor_name: str | None
    specialty: str | None
    tier: str | None
    form_status: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class DashboardListResponse(BaseModel):
    items: list[DashboardListItem]
    total: int
    page: int
    page_size: int


class DashboardFilters(BaseModel):
    geography: str | None = None
    mr_manager_name: str | None = None
    form_status: str | None = None
    specialty: str | None = None
    tier: str | None = None
    page: int = 1
    page_size: int = 25
    sort_by: str = "created_at"
    sort_order: str = "desc"
