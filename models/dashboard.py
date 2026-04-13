import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.config import settings
from core.database import Base

_schema = settings.database_schema


class DashboardFact(Base):
    __tablename__ = "dashboard_fact"
    __table_args__ = {"schema": _schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    submission_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    mr_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    mr_name: Mapped[str | None] = mapped_column(String(255))
    mr_manager_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    mr_manager_name: Mapped[str | None] = mapped_column(String(255))

    geography: Mapped[str | None] = mapped_column(String(100), index=True)
    doctor_name: Mapped[str | None] = mapped_column(String(255))
    specialty: Mapped[str | None] = mapped_column(String(255))
    tier: Mapped[str | None] = mapped_column(String(255))
    form_status: Mapped[str | None] = mapped_column(String(50), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())
