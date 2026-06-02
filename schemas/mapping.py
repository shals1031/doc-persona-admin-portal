from pydantic import BaseModel
from typing import Optional


class MappingFilterParams(BaseModel):
    """Query params for the listing endpoint."""
    doctor_name: Optional[str] = None      # free-text search
    mr_name: Optional[str] = None          # free-text search
    manager_name: Optional[str] = None     # free-text search
    page: int = 1
    page_size: int = 15


class DoctorMRMappingRead(BaseModel):
    """Single row in the table."""
    id: str
    doctor_id: str
    doctor_name: str
    doctor_speciality: Optional[str] = None
    geolocation: Optional[str] = None
    mr_user_id: Optional[str] = None
    mr_name: Optional[str] = None           # None → display "Unassigned" in UI
    manager_name: Optional[str] = None      # None → display "—" in UI

    model_config = {"from_attributes": True}


class MappingListResponse(BaseModel):
    """Paginated list response."""
    items: list[DoctorMRMappingRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class RemapRequest(BaseModel):
    """Body for the remap PATCH endpoint."""
    new_mr_user_id: str
    new_mr_name: str


class RemapResponse(BaseModel):
    """Confirmation returned after remap."""
    doctor_id: str
    doctor_name: str
    old_mr_name: Optional[str] = None
    new_mr_name: str
    message: str


class BulkRemapRequest(BaseModel):
    """Body for the bulk remap endpoint."""
    doctor_ids: list[str]
    new_mr_user_id: str


class BulkRemapResponse(BaseModel):
    """Confirmation returned after bulk remap."""
    remapped_count: int
    new_mr_name: str
    message: str
