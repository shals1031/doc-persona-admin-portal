import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from core.database import Base


class Form(Base):
    __tablename__ = "forms"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    versions = relationship("FormVersion", back_populates="form", cascade="all, delete-orphan")


class FormVersion(Base):
    __tablename__ = "form_versions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "form_id", "version_number", name="uq_form_versions_tenant_form_version"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    form_id = Column(UUID(as_uuid=True), ForeignKey("public.forms.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    version_string = Column(String(50), nullable=False)
    schema_json = Column(JSONB, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)
    is_current = Column(Boolean, default=False, nullable=False)
    changelog = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    form = relationship("Form", back_populates="versions")
