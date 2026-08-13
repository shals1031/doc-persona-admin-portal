import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.config import settings
from core.database import Base

_schema = settings.database_schema


class Persona(Base):
    """Persona master (ai.persona)."""

    __tablename__ = "persona"
    __table_args__ = {"schema": _schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class Brand(Base):
    """Brand master (ai.brands), e.g. NVM-LC / Comig."""

    __tablename__ = "brands"
    __table_args__ = {"schema": _schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class DoctorBrandEngagement(Base):
    """Per-doctor, per-brand engagement (ai.doctor_brand_engagement)."""

    __tablename__ = "doctor_brand_engagement"
    __table_args__ = {"schema": _schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(100), nullable=True)
    response: Mapped[str] = mapped_column(String(255), nullable=True)
    key_lever: Mapped[str] = mapped_column(String(255), nullable=True)
    strategy: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)


class BrandStrategy(Base):
    """Per tenant/brand (+optional persona) strategy (ai.brand_strategy)."""

    __tablename__ = "brand_strategy"
    __table_args__ = {"schema": _schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    persona_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=True)
    strategy: Mapped[str] = mapped_column(Text, nullable=True)
    mr_approach: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)


class CampaignMaterial(Base):
    """Campaign / promotional materials (ai.campaign_material)."""

    __tablename__ = "campaign_material"
    __table_args__ = {"schema": _schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=True)
    persona_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    persona_name: Mapped[str] = mapped_column(String(255), nullable=True)
    material_type: Mapped[str] = mapped_column(String(50), nullable=True)
    # Availability period for the material: whether it applies to a quarter or
    # a month, and the concrete value (e.g. "Q1" or "April").
    period_type: Mapped[str] = mapped_column(String(20), nullable=True)
    period_value: Mapped[str] = mapped_column(String(50), nullable=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=True)
    # Raw file bytes stored directly in the DB (BYTEA); replaces the old
    # on-disk static path that used to live in this column.
    file_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=True)
    # Lifecycle status driving the Push / Recall action: ready / pushed / recalled.
    status: Mapped[str] = mapped_column(String(50), nullable=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)


class DoctorBehavioralProfile(Base):
    """Per-doctor behavioral / persona profile (ai.doctor_behavioral_profile)."""

    __tablename__ = "doctor_behavioral_profile"
    __table_args__ = {"schema": _schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    mr_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    category: Mapped[str] = mapped_column(String(50), nullable=True)
    confidence: Mapped[str] = mapped_column(String(50), nullable=True)

    persona_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    opportunity_score: Mapped[int] = mapped_column(Integer, nullable=True)
    opportunity_tier: Mapped[str] = mapped_column(String(50), nullable=True)

    rich_description: Mapped[str] = mapped_column(Text, nullable=True)
    mr_guidelines: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
