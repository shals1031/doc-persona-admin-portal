import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.config import settings
from core.database import Base

_schema = settings.database_schema


class DoctorProfileFlatTable(Base):
    __tablename__ = "doctor_profile_flat_table"
    __table_args__ = {"schema": _schema}

    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mr_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    mr_name: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    doctor_name: Mapped[str | None] = mapped_column(Text)
    specialty: Mapped[str | None] = mapped_column(Text)
    tier: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)


class DoctorAiProfile(Base):
    __tablename__ = "doctor_ai_profile"
    __table_args__ = {"schema": _schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True)

    mr_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    region: Mapped[str | None] = mapped_column(Text)

    doctor_name: Mapped[str | None] = mapped_column(Text)
    specialty: Mapped[str | None] = mapped_column(Text)

    tier: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(Text)

    summary: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(Vector(768))

    persona_tag: Mapped[str | None] = mapped_column(Text)
    persona_confidence: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())


class DoctorPersonaHistory(Base):
    __tablename__ = "doctor_persona_history"
    __table_args__ = {"schema": _schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_ai_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    old_persona: Mapped[str | None] = mapped_column(Text)
    new_persona: Mapped[str | None] = mapped_column(Text)

    change_reason: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
