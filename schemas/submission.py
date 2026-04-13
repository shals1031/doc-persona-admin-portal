import uuid
from datetime import datetime

from pydantic import BaseModel


class SubmissionDetail(BaseModel):
    submission_id: uuid.UUID
    mr_id: uuid.UUID | None
    mr_name: str | None
    region: str | None
    doctor_name: str | None
    specialty: str | None
    tier: str | None
    confidence: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class AiProfileDetail(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID | None
    doctor_name: str | None
    specialty: str | None
    tier: str | None
    summary: str | None
    persona_tag: str | None
    persona_confidence: float | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class SubmissionWithAiProfile(BaseModel):
    submission: SubmissionDetail
    ai_profile: AiProfileDetail | None
