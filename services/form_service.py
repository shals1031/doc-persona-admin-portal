import copy
import uuid as _uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from models.form import Form, FormVersion
from schemas.form import (
    CreateFormRequest,
    CreateFormVersionRequest,
    PublishFormVersionRequest,
    UpdateFormRequest,
    UpdateSchemaRequest,
)




class FormService:
    """
    Handles all form-management operations against the shared ``public.forms``
    and ``public.form_versions`` Postgres tables.  This is a line-by-line port
    of the NestJS ``FormsService``.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Form CRUD ────────────────────────────────────────────────────

    async def create_form(
        self, data: CreateFormRequest, user_id: str, user_role: str, tenant_id: _uuid.UUID,
    ) -> Dict[str, Any]:
        if user_role == "SYSTEM_ADMIN" and data.tenantId:
            resolved_tenant = data.tenantId
        elif tenant_id:
            resolved_tenant = tenant_id
        else:
            raise HTTPException(status_code=400, detail="Tenant ID is required to create a form.")
        form = Form(
            tenant_id=resolved_tenant,
            name=data.name,
            description=data.description,
            category=data.category,
            created_by=user_id,
        )
        self.db.add(form)
        await self.db.commit()
        await self.db.refresh(form)
        return self._form_to_dict(form)

    async def get_all_forms(self, tenant_id: _uuid.UUID) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(Form).where(Form.tenant_id == tenant_id).order_by(Form.created_at.desc())
        )
        forms = result.scalars().all()

        # Fetch current version string for each form (Issue 3)
        out: List[Dict[str, Any]] = []
        for f in forms:
            d = self._form_to_dict(f)
            v_result = await self.db.execute(
                select(FormVersion.version_string)
                .where(FormVersion.form_id == f.id, FormVersion.is_current == True)
            )
            row = v_result.first()
            d["currentVersion"] = row[0] if row else None
            out.append(d)
        return out

    async def get_form(self, form_id: str, tenant_id: _uuid.UUID) -> Form:
        result = await self.db.execute(select(Form).where(Form.id == form_id, Form.tenant_id == tenant_id))
        form = result.scalar_one_or_none()
        if not form:
            raise HTTPException(status_code=404, detail=f"Form {form_id} not found")
        return form

    async def get_form_with_current_version(self, form_id: str, tenant_id: _uuid.UUID) -> Dict[str, Any]:
        form = await self.get_form(form_id, tenant_id)

        v_result = await self.db.execute(
            select(FormVersion)
            .where(FormVersion.form_id == form_id, FormVersion.is_current == True, FormVersion.tenant_id == tenant_id)
        )
        current_version = v_result.scalar_one_or_none()

        form_dict = self._form_to_dict(form)
        form_dict["versions"] = [self._version_to_dict(current_version)] if current_version else []
        return form_dict

    async def update_form(
        self, form_id: str, data: UpdateFormRequest, user_role: str, tenant_id: _uuid.UUID,
    ) -> Dict[str, Any]:
        if user_role not in ("ADMIN", "SYSTEM_ADMIN"):
            raise HTTPException(status_code=403, detail="Only admins can update forms")
        form = await self.get_form(form_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)
        # Map camelCase isActive → snake_case is_active
        if "isActive" in update_data:
            update_data["is_active"] = update_data.pop("isActive")
        for key, val in update_data.items():
            setattr(form, key, val)
        self.db.add(form)
        await self.db.commit()
        await self.db.refresh(form)
        return self._form_to_dict(form)

    async def remove_form(self, form_id: str, user_role: str, tenant_id: _uuid.UUID) -> None:
        if user_role not in ("ADMIN", "SYSTEM_ADMIN"):
            raise HTTPException(status_code=403, detail="Only admins can delete forms")
        form = await self.get_form(form_id, tenant_id)
        form.is_active = False
        self.db.add(form)
        await self.db.commit()

    # ─── Version Management ───────────────────────────────────────────

    async def get_versions(self, form_id: str, tenant_id: _uuid.UUID) -> List[Dict[str, Any]]:
        await self.get_form(form_id, tenant_id)  # ensure exists
        result = await self.db.execute(
            select(FormVersion)
            .where(FormVersion.form_id == form_id, FormVersion.tenant_id == tenant_id)
            .order_by(FormVersion.version_number.desc())
        )
        return [self._version_to_dict(v) for v in result.scalars().all()]

    async def get_version(self, form_id: str, version_id: str, tenant_id: _uuid.UUID) -> Dict[str, Any]:
        await self.get_form(form_id, tenant_id)
        result = await self.db.execute(
            select(FormVersion)
            .where(FormVersion.id == version_id, FormVersion.form_id == form_id)
        )
        version = result.scalar_one_or_none()
        if not version:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version_id} not found for form {form_id}",
            )
        return self._version_to_dict(version)

    async def get_latest_version(self, form_id: str, tenant_id: _uuid.UUID) -> FormVersion:
        result = await self.db.execute(
            select(FormVersion)
            .where(FormVersion.form_id == form_id, FormVersion.is_current == True, FormVersion.tenant_id == tenant_id)
        )
        version = result.scalar_one_or_none()
        if not version:
            raise HTTPException(
                status_code=404,
                detail=f"No current version found for form {form_id}",
            )
        return version

    async def get_latest_draft_version(self, form_id: str, tenant_id: _uuid.UUID) -> Optional[FormVersion]:
        # A draft is the absolute latest version IF it is not currently active.
        result = await self.db.execute(
            select(FormVersion)
            .where(FormVersion.form_id == form_id, FormVersion.tenant_id == tenant_id)
            .order_by(FormVersion.created_at.desc())
        )
        latest_version = result.scalars().first()
        if latest_version and not latest_version.is_current:
            return latest_version
        return None

    async def create_version(
        self, form_id: str, data: CreateFormVersionRequest, user_id: str, user_role: str, tenant_id: _uuid.UUID,
    ) -> Dict[str, Any]:
        if user_role not in ("ADMIN", "SYSTEM_ADMIN"):
            raise HTTPException(status_code=403, detail="Only admins can create form versions")
        form = await self.get_form(form_id, tenant_id)
        await self.validate_form_schema(data.schemaJson)

        # Get next version number
        max_result = await self.db.execute(
            select(FormVersion)
            .where(FormVersion.form_id == form_id, FormVersion.tenant_id == tenant_id)
            .order_by(FormVersion.version_number.desc())
        )
        max_v = max_result.scalars().first()
        next_number = (max_v.version_number + 1) if max_v else 1

        # Synchronize version string from schema if present
        version_string = data.schemaJson.get("version") or data.versionString
        schema_json = {**data.schemaJson, "version": version_string}

        version = FormVersion(
            tenant_id=form.tenant_id,
            form_id=form_id,
            version_number=next_number,
            version_string=version_string,
            schema_json=schema_json,
            changelog=data.changelog,
            created_by=user_id,
            is_published=False,
            is_current=False,
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return self._version_to_dict(version)

    async def publish_version(
        self, form_id: str, version_id: str, data: PublishFormVersionRequest,
        user_id: str, user_role: str, tenant_id: _uuid.UUID,
    ) -> Dict[str, Any]:
        if user_role not in ("ADMIN", "SYSTEM_ADMIN"):
            raise HTTPException(status_code=403, detail="Only admins can publish form versions")
        await self.get_form(form_id, tenant_id)

        result = await self.db.execute(
            select(FormVersion)
            .where(FormVersion.id == version_id, FormVersion.form_id == form_id)
        )
        version = result.scalar_one_or_none()
        if not version:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version_id} not found for form {form_id}",
            )
        if version.is_published:
            if not data.setAsCurrent or version.is_current:
                raise HTTPException(status_code=400, detail="This version is already published")

        set_as_current = data.setAsCurrent is not False

        if set_as_current:
            # Unset current from all other versions
            current_result = await self.db.execute(
                select(FormVersion)
                .where(FormVersion.form_id == form_id, FormVersion.is_current == True, FormVersion.tenant_id == tenant_id)
            )
            for v in current_result.scalars().all():
                v.is_current = False
                self.db.add(v)

        version.is_published = True
        version.is_current = set_as_current
        version.published_at = datetime.utcnow()
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return self._version_to_dict(version)

    async def update_version_schema(
        self, form_id: str, version_id: str, data: UpdateSchemaRequest,
        user_id: str, user_role: str, tenant_id: _uuid.UUID,
    ) -> Dict[str, Any]:
        if user_role not in ("ADMIN", "SYSTEM_ADMIN"):
            raise HTTPException(status_code=403, detail="Only admins can update form schemas")
        await self.get_form(form_id, tenant_id)

        result = await self.db.execute(
            select(FormVersion)
            .where(FormVersion.id == version_id, FormVersion.form_id == form_id)
        )
        version = result.scalar_one_or_none()
        if not version:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version_id} not found for form {form_id}",
            )
        if version.is_published and version.is_current:
            raise HTTPException(status_code=400, detail="Cannot edit a currently active version")

        # Optionally update version string if provided in schema
        if "version" in data.schemaJson:
            version.version_string = data.schemaJson["version"]
            
        version.schema_json = data.schemaJson
        version.is_published = False  # Any edit drops the form back into a Draft state
        version.updated_at = datetime.utcnow()
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return self._version_to_dict(version)

    async def validate_form_schema(self, schema: dict) -> bool:
        if not schema.get("formId") or not schema.get("version") or not schema.get("name"):
            raise HTTPException(
                status_code=400,
                detail="Schema must contain formId, version, and name",
            )
        if not isinstance(schema.get("sections"), list):
            raise HTTPException(status_code=400, detail="Schema must contain sections array")
        if not isinstance(schema.get("questions"), list):
            raise HTTPException(status_code=400, detail="Schema must contain questions array")
        return True

    # ─── Versioning Helpers ───────────────────────────────────────────

    # ─── Serializers ─────────────────────────────────────────────────

    def _form_to_dict(self, form: Form) -> Dict[str, Any]:
        return {
            "id": str(form.id),
            "tenantId": str(form.tenant_id),
            "name": form.name,
            "description": form.description,
            "category": form.category,
            "isActive": form.is_active,
            "createdAt": form.created_at.isoformat() if form.created_at else None,
            "updatedAt": form.updated_at.isoformat() if form.updated_at else None,
        }

    def _version_to_dict(self, v: FormVersion) -> Dict[str, Any]:
        return {
            "id": str(v.id),
            "formId": str(v.form_id),
            "versionNumber": v.version_number,
            "versionString": v.version_string,
            "schemaJson": v.schema_json,
            "isPublished": v.is_published,
            "isCurrent": v.is_current,
            "changelog": v.changelog,
            "publishedAt": v.published_at.isoformat() if v.published_at else None,
            "createdAt": v.created_at.isoformat() if v.created_at else None,
        }
