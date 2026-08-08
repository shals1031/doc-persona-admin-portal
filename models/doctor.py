from __future__ import annotations
from typing import Optional
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
    # tenant_id is verified via join with dashboard_fact to support environments where it might be missing from this table
    mr_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    mr_name: Mapped[str] = mapped_column(Text, nullable=True)
    region: Mapped[str] = mapped_column(Text, nullable=True)
    doctor_name: Mapped[str] = mapped_column(Text, nullable=True)
    specialty: Mapped[str] = mapped_column(Text, nullable=True)
    tier: Mapped[str] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class DoctorAiProfile(Base):
    __tablename__ = "doctor_ai_profile"
    __table_args__ = {"schema": _schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=True)

    mr_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    region: Mapped[str] = mapped_column(Text, nullable=True)

    doctor_name: Mapped[str] = mapped_column(Text, nullable=True)
    specialty: Mapped[str] = mapped_column(Text, nullable=True)

    tier: Mapped[str] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(Text, nullable=True)

    summary: Mapped[str] = mapped_column(Text, nullable=True)
    embedding: Mapped[list] = mapped_column(Vector(768), nullable=True)

    persona_tag: Mapped[str] = mapped_column(Text, nullable=True)
    persona_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)


class DoctorPersonaHistory(Base):
    __tablename__ = "doctor_persona_history"
    __table_args__ = {"schema": _schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_ai_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    old_persona: Mapped[str] = mapped_column(Text, nullable=True)
    new_persona: Mapped[str] = mapped_column(Text, nullable=True)

    change_reason: Mapped[str] = mapped_column(Text, nullable=True)
    model_version: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
