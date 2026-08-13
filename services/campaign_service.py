import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_engagement import Brand, CampaignMaterial, Persona
from models.control import Tenant

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

# Availability period types offered on the upload form.
PERIOD_TYPES = ["Quarter", "Month"]

# Default fiscal-year start month (April) used when a tenant has none set.
DEFAULT_FISCAL_START_MONTH = 4

_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _month_name(month: int) -> str:
    """Return the full month name for a 1-based month number."""
    return _MONTH_NAMES[(month - 1) % 12]


def build_month_options() -> list[str]:
    """Full list of month names for the month-wise dropdown."""
    return list(_MONTH_NAMES)


def build_quarter_options(fiscal_start_month: int) -> list[dict]:
    """Build the four fiscal quarters for a tenant.

    Q1 begins at ``fiscal_start_month`` (April by default, giving Apr-Jun) and
    subsequent quarters are calculated accordingly. Each option carries a
    ``value`` (e.g. ``"Q1"``) and a human-readable ``label`` including the month
    range (e.g. ``"Q1 (Apr-Jun)"``).
    """
    start = ((fiscal_start_month or DEFAULT_FISCAL_START_MONTH) - 1) % 12 + 1
    options: list[dict] = []
    for q in range(4):
        first = ((start - 1 + q * 3) % 12) + 1
        last = ((start - 1 + q * 3 + 2) % 12) + 1
        label = f"Q{q + 1} ({_month_name(first)[:3]}-{_month_name(last)[:3]})"
        options.append({"value": f"Q{q + 1}", "label": label})
    return options


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
        fiscal_start_month = await self._get_fiscal_start_month(tenant_id)
        return {
            "materials": materials,
            "brands": brands,
            "material_types": MATERIAL_TYPES,
            "period_types": PERIOD_TYPES,
            "quarter_options": build_quarter_options(fiscal_start_month),
            "month_options": build_month_options(),
            "summary": summary,
            "filters": {
                "brand_name": brand_name,
                "material_type": material_type,
                "status": status,
            },
        }

    async def _get_fiscal_start_month(self, tenant_id: uuid.UUID) -> int:
        """Return the tenant's fiscal-year start month, defaulting to April."""
        result = await self.db.execute(
            select(Tenant.fiscal_year_start_month).where(Tenant.id == tenant_id)
        )
        row = result.first()
        if row and row[0]:
            return int(row[0])
        return DEFAULT_FISCAL_START_MONTH

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
                "period_type": r.period_type,
                "period_value": r.period_value,
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
        period_type: str | None = None,
        period_value: str | None = None,
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
                period_type=period_type,
                period_value=period_value,
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

