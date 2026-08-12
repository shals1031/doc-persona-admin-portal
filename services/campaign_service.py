import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_engagement import Brand, CampaignMaterial, Persona

# Status badge styling used by the Campaign Materials table (mirrors the Figma).
STATUS_BADGE = {
    "ready": "success",
    "pushed": "primary",
    "recalled": "secondary",
}

# Allowed material types for the Campaign Materials screen.
MATERIAL_TYPES = [
    "Journal Article",
    "Case Study",
    "Product Update",
    "REW",
    "Clinical Practice Guidelines",
    "Others",
]


def _human_size(num_bytes) -> str:
    if not num_bytes:
        return "—"
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


class CampaignService:
    """Reads campaign / promotional materials for the Campaign Materials screen.

    Source: ai.campaign_material (+ ai.brands for the brand filter list).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_page(
        self,
        tenant_id: uuid.UUID,
        brand_name: str | None = None,
        material_type: str | None = None,
        status: str | None = None,
    ) -> dict:
        materials = await self._list_materials(
            tenant_id, brand_name, material_type, status
        )
        brands = await self._list_brands(tenant_id)
        summary = await self._summary(tenant_id)
        return {
            "materials": materials,
            "brands": brands,
            "material_types": MATERIAL_TYPES,
            "summary": summary,
            "filters": {
                "brand_name": brand_name,
                "material_type": material_type,
                "status": status,
            },
        }

    async def _list_materials(
        self,
        tenant_id: uuid.UUID,
        brand_name: str | None,
        material_type: str | None,
        status: str | None,
    ) -> list[dict]:
        stmt = (
            select(CampaignMaterial)
            .where(CampaignMaterial.tenant_id == tenant_id)
            .order_by(CampaignMaterial.created_at.desc())
        )
        if brand_name:
            stmt = stmt.where(CampaignMaterial.brand_name == brand_name)
        if material_type:
            stmt = stmt.where(CampaignMaterial.material_type == material_type)
        if status:
            stmt = stmt.where(CampaignMaterial.status == status)

        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "brand_name": r.brand_name,
                "persona_name": r.persona_name or "All Personas",
                "material_type": r.material_type,
                "file_name": r.file_name,
                "has_file": r.file_data is not None,
                "file_size": _human_size(r.file_size_bytes),
                "status": r.status or "ready",
                "badge": STATUS_BADGE.get((r.status or "ready").lower(), "secondary"),
                "created_at": r.created_at,
            }
            for r in rows
        ]

    async def _list_brands(self, tenant_id: uuid.UUID) -> list[str]:
        result = await self.db.execute(
            select(Brand.name)
            .where(Brand.tenant_id == tenant_id)
            .where(Brand.name.is_not(None))
            .order_by(Brand.name)
        )
        return [row[0] for row in result.all()]

    async def _summary(self, tenant_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(
                CampaignMaterial.status,
                func.count(CampaignMaterial.id),
            )
            .where(CampaignMaterial.tenant_id == tenant_id)
            .group_by(CampaignMaterial.status)
        )
        counts = {(row[0] or "ready").lower(): int(row[1]) for row in result.all()}
        return {
            "total": sum(counts.values()),
            "ready": counts.get("ready", 0),
            "pushed": counts.get("pushed", 0),
            "recalled": counts.get("recalled", 0),
        }

    async def _resolve_brand_id(
        self, tenant_id: uuid.UUID, brand_name: str | None
    ) -> uuid.UUID | None:
        """Look up the brand id for a brand name within the tenant."""
        if not brand_name:
            return None
        result = await self.db.execute(
            select(Brand.id)
            .where(Brand.tenant_id == tenant_id)
            .where(Brand.name == brand_name)
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None

    async def _resolve_persona_id(
        self, persona_name: str | None
    ) -> uuid.UUID | None:
        """Look up the persona id for a persona name."""
        if not persona_name:
            return None
        result = await self.db.execute(
            select(Persona.id).where(Persona.name == persona_name).limit(1)
        )
        row = result.first()
        return row[0] if row else None

    async def create_material(
        self,
        tenant_id: uuid.UUID,
        uploaded_by: uuid.UUID | None,
        brand_name: str | None,
        persona_name: str | None,
        material_type: str | None,
        file_name: str | None,
        file_data: bytes | None = None,
        file_size_bytes: int | None = None,
    ) -> list[CampaignMaterial]:
        """Create one campaign material row per selected persona.

        When multiple personas are selected the ``persona_name`` field arrives
        comma-separated; a separate row (with its resolved ``persona_id``) is
        inserted for each persona.
        """
        brand_id = await self._resolve_brand_id(tenant_id, brand_name)

        personas = [
            p.strip() for p in (persona_name or "").split(",") if p.strip()
        ] or ["All Personas"]

        materials: list[CampaignMaterial] = []
        for persona in personas:
            persona_id = await self._resolve_persona_id(persona)
            material = CampaignMaterial(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                brand_id=brand_id,
                brand_name=brand_name,
                persona_id=persona_id,
                persona_name=persona,
                material_type=material_type,
                file_name=file_name,
                file_data=file_data,
                file_size_bytes=file_size_bytes,
                status="ready",
                uploaded_by=uploaded_by,
            )
            self.db.add(material)
            materials.append(material)

        await self.db.commit()
        return materials

    async def get_material_file(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID
    ) -> tuple[str | None, bytes | None] | None:
        """Return (file_name, file_data) for the given material, or None."""
        result = await self.db.execute(
            select(CampaignMaterial.file_name, CampaignMaterial.file_data)
            .where(CampaignMaterial.id == material_id)
            .where(CampaignMaterial.tenant_id == tenant_id)
        )
        row = result.first()
        if row is None:
            return None
        return row[0], row[1]

    async def set_status(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID, status: str
    ) -> None:
        await self.db.execute(
            update(CampaignMaterial)
            .where(CampaignMaterial.id == material_id)
            .where(CampaignMaterial.tenant_id == tenant_id)
            .values(status=status)
        )
        await self.db.commit()

