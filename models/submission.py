import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base

class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submitted_by = Column(UUID(as_uuid=True), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(50), nullable=True)
