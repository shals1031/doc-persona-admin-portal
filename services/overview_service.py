import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_engagement import (
    BrandStrategy,
    DoctorBehavioralProfile,
    DoctorBrandEngagement,
    Persona,
)
from models.auth import Doctor, MRDoctorMapping, Territory
from models.doctor import DoctorPersona

# Persona ordering + colours used across the Overview (donut) and the
# Persona Mix "Strategy & Analytics" bar chart. Colours mirror the Figma.
PERSONA_ORDER = [
    "Evidence Champion",
    "Practical Pragmatist",
    "Price Guardian",
    "Loyal Incumbent",
    "Relationship Builder",
    "Early Mover",
]

PERSONA_COLORS = {
    "Evidence Champion": "#14b8a6",
    "Practical Pragmatist": "#b45309",
    "Price Guardian": "#2563eb",
    "Loyal Incumbent": "#dc2626",
    "Relationship Builder": "#db2777",
    "Early Mover": "#7c3aed",
}

# Brands whose engagement status is charted on the Overview donuts.
BRAND_ORDER = ["NVM-LC", "Comig"]

# Canonical brand-engagement status ordering + colours (mirrors the Figma).
BRAND_STATUS_ORDER = [
    "Preferred",
    "Regular",
    "Occasional",
    "Aware",
    "Not aware",
]

BRAND_STATUS_COLORS = {
    "Preferred": "#16a34a",
    "Regular": "#2563eb",
    "Occasional": "#f59e0b",
    "Aware": "#94a3b8",
    "Not aware": "#dc2626",
}


def _status_color(status: str) -> str:
    """Best-effort colour lookup that tolerates variant status labels."""
    if not status:
        return "#cbd5e1"
    if status in BRAND_STATUS_COLORS:
        return BRAND_STATUS_COLORS[status]
    low = status.lower()
    for key, color in BRAND_STATUS_COLORS.items():
        if key.lower() in low:
            return color
    return "#94a3b8"


class OverviewService:
    """Aggregates high-level analytics for the Dashboard Overview page.

    Data sources:
      * core.doctors / core.mr_doctor_mapping -> doctor counts + mapping status
      * core.submissions + core.doctor_ai_profile -> persona mix (persona_tag)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_regions(self, tenant_id: uuid.UUID) -> list[dict]:
        """Territories for the tenant, used to populate the 'All Regions' filter."""
        result = await self.db.execute(
            select(Territory.id, Territory.name)
            .where(Territory.tenant_id == tenant_id)
            .order_by(Territory.name)
        )
        return [{"id": str(row.id), "name": row.name} for row in result.all()]

    async def get_personas(self, tenant_id: uuid.UUID) -> list[dict]:
        """Persona master (ai.persona) used to populate the 'All Personas' filter.

        Only personas that are actually assigned to at least one doctor of the
        tenant are returned so the dropdown stays tenant-specific.
        """
        result = await self.db.execute(
            select(Persona.id, Persona.name)
            .join(DoctorPersona, DoctorPersona.persona_id == Persona.id)
            .where(DoctorPersona.tenant_id == tenant_id)
            .group_by(Persona.id, Persona.name)
            .order_by(Persona.name)
        )
        return [{"id": str(row.id), "name": row.name} for row in result.all()]

    def _filtered_doctor_ids(
        self,
        tenant_id: uuid.UUID,
        region_id: uuid.UUID | None,
        persona_id: uuid.UUID | None,
    ):
        """Sub-select of core.doctors ids matching tenant + region + persona."""
        stmt = select(Doctor.id).where(Doctor.tenant_id == tenant_id)
        if region_id is not None:
            stmt = stmt.where(Doctor.territory_id == region_id)
        if persona_id is not None:
            stmt = stmt.where(
                Doctor.id.in_(
                    select(DoctorPersona.doctor_id).where(
                        DoctorPersona.tenant_id == tenant_id,
                        DoctorPersona.persona_id == persona_id,
                    )
                )
            )
        return stmt

    async def get_overview(
        self,
        tenant_id: uuid.UUID,
        region_id: uuid.UUID | None = None,
        persona_id: uuid.UUID | None = None,
    ) -> dict:
        total_doctors = await self._count_total_doctors(tenant_id, region_id, persona_id)
        mapped = await self._count_mapped_doctors(tenant_id, region_id, persona_id)
        unmapped = max(total_doctors - mapped, 0)

        persona_mix = await self._persona_mix(tenant_id, region_id, persona_id)
        profiled = await self._count_profiled_doctors(tenant_id, region_id, persona_id)
        profiling_completion = round((profiled / total_doctors) * 100) if total_doctors else 0

        brand_status = await self._brand_status(tenant_id, region_id, persona_id)

        return {
            "total_doctors": total_doctors,
            "mapped": mapped,
            "unmapped": unmapped,
            "profiling_completion": profiling_completion,
            "persona_mix": persona_mix,
            "persona_total": sum(p["count"] for p in persona_mix),
            "brand_status": brand_status,
        }

    async def _count_total_doctors(
        self,
        tenant_id: uuid.UUID,
        region_id: uuid.UUID | None = None,
        persona_id: uuid.UUID | None = None,
    ) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(
                self._filtered_doctor_ids(tenant_id, region_id, persona_id).subquery()
            )
        )
        return int(result.scalar_one() or 0)

    async def _count_mapped_doctors(
        self,
        tenant_id: uuid.UUID,
        region_id: uuid.UUID | None = None,
        persona_id: uuid.UUID | None = None,
    ) -> int:
        doctor_ids = self._filtered_doctor_ids(tenant_id, region_id, persona_id)
        result = await self.db.execute(
            select(func.count(func.distinct(MRDoctorMapping.doctor_id)))
            .where(MRDoctorMapping.tenant_id == tenant_id)
            .where(MRDoctorMapping.doctor_id.in_(doctor_ids))
        )
        return int(result.scalar_one() or 0)

    async def _count_profiled_doctors(
        self,
        tenant_id: uuid.UUID,
        region_id: uuid.UUID | None = None,
        persona_id: uuid.UUID | None = None,
    ) -> int:
        """Number of doctors that have an entry in ai.doctor_persona (profiled)."""
        doctor_ids = self._filtered_doctor_ids(tenant_id, region_id, persona_id)
        result = await self.db.execute(
            select(func.count(func.distinct(DoctorPersona.doctor_id)))
            .where(DoctorPersona.tenant_id == tenant_id)
            .where(DoctorPersona.doctor_id.in_(doctor_ids))
        )
        return int(result.scalar_one() or 0)

    async def _persona_mix(
        self,
        tenant_id: uuid.UUID,
        region_id: uuid.UUID | None = None,
        persona_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Count distinct doctors per persona for the tenant.

        Source: ai.doctor_persona joined to ai.persona (persona master),
        restricted to the tenant and the selected region/persona filters.
        """
        doctor_ids = self._filtered_doctor_ids(tenant_id, region_id, persona_id)
        result = await self.db.execute(
            select(
                Persona.name.label("persona"),
                func.count(func.distinct(DoctorPersona.doctor_id)).label("count"),
            )
            .select_from(DoctorPersona)
            .join(Persona, Persona.id == DoctorPersona.persona_id)
            .where(DoctorPersona.tenant_id == tenant_id)
            .where(DoctorPersona.doctor_id.in_(doctor_ids))
            .group_by(Persona.name)
        )
        counts = {row.persona: int(row.count) for row in result.all()}

        # Resolve persona name -> id so the Persona Mix chart/legend can link to
        # the /persona-mix page filtered by the selected persona.
        id_result = await self.db.execute(select(Persona.id, Persona.name))
        name_to_id = {row.name: str(row.id) for row in id_result.all()}

        # Return in the canonical persona order, keeping any extra tags at the end.
        mix: list[dict] = []
        for persona in PERSONA_ORDER:
            mix.append({
                "persona": persona,
                "persona_id": name_to_id.get(persona),
                "count": counts.pop(persona, 0),
                "color": PERSONA_COLORS.get(persona, "#94a3b8"),
            })
        for persona, count in counts.items():
            mix.append({
                "persona": persona,
                "persona_id": name_to_id.get(persona),
                "count": count,
                "color": "#94a3b8",
            })
        return mix

    async def _brand_status(
        self,
        tenant_id: uuid.UUID,
        region_id: uuid.UUID | None = None,
        persona_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Brand-engagement status distribution per brand for the Overview donuts.

        Source: ai.doctor_brand_engagement (status per doctor per brand),
        grouped by brand_name + status for the tenant, restricted to the
        doctors matching the selected region/persona filters.
        """
        doctor_ids = self._filtered_doctor_ids(tenant_id, region_id, persona_id)
        result = await self.db.execute(
            select(
                DoctorBrandEngagement.brand_name.label("brand"),
                DoctorBrandEngagement.status.label("status"),
                func.count(DoctorBrandEngagement.id).label("count"),
            )
            .where(DoctorBrandEngagement.tenant_id == tenant_id)
            .where(DoctorBrandEngagement.brand_name.is_not(None))
            .where(DoctorBrandEngagement.doctor_id.in_(doctor_ids))
            .group_by(DoctorBrandEngagement.brand_name, DoctorBrandEngagement.status)
        )

        # brand -> {status -> count}
        by_brand: dict[str, dict[str, int]] = {}
        for row in result.all():
            by_brand.setdefault(row.brand, {})[row.status or "Unknown"] = int(row.count)

        # Keep the canonical brands first, then any additional brands found.
        brand_names = list(BRAND_ORDER)
        for name in by_brand:
            if name not in brand_names:
                brand_names.append(name)

        brands: list[dict] = []
        for name in brand_names:
            status_counts = by_brand.get(name, {})
            statuses: list[dict] = []
            # Canonical status order first.
            seen = set()
            for status in BRAND_STATUS_ORDER:
                count = status_counts.get(status, 0)
                if count:
                    statuses.append({
                        "status": status,
                        "count": count,
                        "color": _status_color(status),
                    })
                    seen.add(status)
            # Any non-canonical statuses.
            for status, count in status_counts.items():
                if status not in seen and count:
                    statuses.append({
                        "status": status,
                        "count": count,
                        "color": _status_color(status),
                    })
            brands.append({
                "brand": name,
                "statuses": statuses,
                "total": sum(s["count"] for s in statuses),
            })
        return brands

    async def get_persona_strategy(
        self,
        tenant_id: uuid.UUID,
        region_id: uuid.UUID | None = None,
        persona_id: uuid.UUID | None = None,
    ) -> dict:
        """Data for the Persona Mix -> "Strategy & Analytics" page.

        Combines:
          * persona counts (reuses the Overview persona mix)
          * behavioral opportunity tiers from ai.doctor_behavioral_profile
          * per-brand strategy narratives from ai.brand_strategy
        """
        total_profiled = await self._count_profiled_doctors(tenant_id, region_id)
        persona_mix = await self._persona_mix(tenant_id, region_id, persona_id)
        persona_total = sum(p["count"] for p in persona_mix)

        for p in persona_mix:
            p["global_pct"] = round((p["count"] / total_profiled * 100), 1) if total_profiled else 0

        opportunity = await self._opportunity_tiers(tenant_id, region_id, persona_id)
        strategies = await self._brand_strategies(tenant_id, persona_id)

        # Extract MR Approach narrative
        mr_approach = None
        for s in strategies:
            if s.get("mr_approach"):
                mr_approach = s["mr_approach"]
                break

        if not mr_approach and persona_id:
            res = await self.db.execute(
                select(DoctorBehavioralProfile.mr_guidelines)
                .where(
                    DoctorBehavioralProfile.tenant_id == tenant_id,
                    DoctorBehavioralProfile.persona_id == persona_id,
                    DoctorBehavioralProfile.mr_guidelines.is_not(None),
                )
                .limit(1)
            )
            mr_approach = res.scalar_one_or_none()

        # When a specific persona is selected, resolve its name + colour so the
        # page can highlight which persona the data belongs to.
        selected_persona = None
        if persona_id is not None:
            res = await self.db.execute(
                select(Persona.name).where(Persona.id == persona_id)
            )
            name = res.scalar_one_or_none()
            if name:
                selected_persona = {
                    "id": str(persona_id),
                    "name": name,
                    "color": PERSONA_COLORS.get(name, "#94a3b8"),
                }

        return {
            "persona_mix": persona_mix,
            "persona_total": persona_total,
            "total_profiled": total_profiled,
            "opportunity": opportunity,
            "strategies": strategies,
            "mr_approach": mr_approach,
            "selected_persona": selected_persona,
        }

    async def _opportunity_tiers(
        self,
        tenant_id: uuid.UUID,
        region_id: uuid.UUID | None = None,
        persona_id: uuid.UUID | None = None,
    ) -> list[dict]:
        doctor_ids = self._filtered_doctor_ids(tenant_id, region_id, persona_id)
        stmt = (
            select(
                DoctorBehavioralProfile.opportunity_tier.label("tier"),
                func.count(DoctorBehavioralProfile.id).label("count"),
            )
            .where(DoctorBehavioralProfile.tenant_id == tenant_id)
            .where(DoctorBehavioralProfile.opportunity_tier.is_not(None))
            .where(DoctorBehavioralProfile.doctor_id.in_(doctor_ids))
            .group_by(DoctorBehavioralProfile.opportunity_tier)
        )
        result = await self.db.execute(stmt)
        counts = {row.tier: int(row.count) for row in result.all()}
        tier_colors = {"High": "#16a34a", "Medium": "#f59e0b", "Low": "#94a3b8"}
        tiers: list[dict] = []
        for tier in ["High", "Medium", "Low"]:
            tiers.append({
                "tier": tier,
                "count": counts.pop(tier, 0),
                "color": tier_colors.get(tier, "#94a3b8"),
            })
        for tier, count in counts.items():
            tiers.append({"tier": tier, "count": count, "color": "#94a3b8"})
        return tiers

    async def _brand_strategies(
        self,
        tenant_id: uuid.UUID,
        persona_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Per-brand strategy narratives joined to their persona.

        Each strategy carries its persona name + colour so the page can label
        every card. When ``persona_id`` is provided, only that persona's
        strategies are returned.
        """
        stmt = (
            select(
                BrandStrategy.brand_name,
                BrandStrategy.strategy,
                BrandStrategy.mr_approach,
                BrandStrategy.persona_id,
                Persona.name.label("persona_name"),
            )
            .select_from(BrandStrategy)
            .join(Persona, Persona.id == BrandStrategy.persona_id, isouter=True)
            .where(BrandStrategy.tenant_id == tenant_id)
        )
        if persona_id is not None:
            stmt = stmt.where(BrandStrategy.persona_id == persona_id)
        stmt = stmt.order_by(Persona.name, BrandStrategy.brand_name)

        result = await self.db.execute(stmt)
        return [
            {
                "brand_name": r.brand_name,
                "strategy": r.strategy,
                "mr_approach": r.mr_approach,
                "persona_id": str(r.persona_id) if r.persona_id else None,
                "persona_name": r.persona_name,
                "persona_color": PERSONA_COLORS.get(r.persona_name, "#94a3b8"),
            }
            for r in result.all()
        ]
