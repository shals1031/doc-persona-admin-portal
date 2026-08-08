import uuid
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base

class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = {"schema": "core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submitted_by = Column(UUID(as_uuid=True), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
