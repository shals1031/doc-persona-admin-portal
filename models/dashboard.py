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
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    mr_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    mr_name: Mapped[str] = mapped_column(String(255), nullable=True)
    mr_manager_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    mr_manager_name: Mapped[str] = mapped_column(String(255), nullable=True)

    geography: Mapped[str] = mapped_column(String(100), index=True, nullable=True)
    doctor_name: Mapped[str] = mapped_column(String(255), nullable=True)
    specialty: Mapped[str] = mapped_column(String(255), nullable=True)
    tier: Mapped[str] = mapped_column(String(255), nullable=True)
    form_status: Mapped[str] = mapped_column(String(50), index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
