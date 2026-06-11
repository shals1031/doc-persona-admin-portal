from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ─── Form CRUD Schemas ───────────────────────────────────────────────

class CreateFormRequest(BaseModel):
    tenantId: Optional[str] = None
    name: str
    description: Optional[str] = None
    category: Optional[str] = None


class UpdateFormRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    isActive: Optional[bool] = None


# ─── Version Schemas ─────────────────────────────────────────────────

class CreateFormVersionRequest(BaseModel):
    versionString: str
    schemaJson: Dict[str, Any]
    changelog: Optional[str] = None


class PublishFormVersionRequest(BaseModel):
    setAsCurrent: Optional[bool] = True


class UpdateSchemaRequest(BaseModel):
    schemaJson: Dict[str, Any]



