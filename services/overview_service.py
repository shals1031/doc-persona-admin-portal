import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_engagement import (
    BrandStrategy,
    DoctorBehavioralProfile,
    DoctorBrandEngagement,
)
from models.auth import Doctor, MRDoctorMapping
from models.doctor import DoctorAiProfile
from models.submission import Submission

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

    async def get_overview(self, tenant_id: uuid.UUID) -> dict:
        total_doctors = await self._count_total_doctors(tenant_id)
        mapped = await self._count_mapped_doctors(tenant_id)
        unmapped = max(total_doctors - mapped, 0)

        persona_mix = await self._persona_mix(tenant_id)
        profiled = sum(p["count"] for p in persona_mix)
        profiling_completion = round((profiled / total_doctors) * 100) if total_doctors else 0

        brand_status = await self._brand_status(tenant_id)

        return {
            "total_doctors": total_doctors,
            "mapped": mapped,
            "unmapped": unmapped,
            "profiling_completion": profiling_completion,
            "persona_mix": persona_mix,
            "persona_total": profiled,
            "brand_status": brand_status,
        }

    async def _count_total_doctors(self, tenant_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Doctor.id)).where(Doctor.tenant_id == tenant_id)
        )
        return int(result.scalar_one() or 0)

    async def _count_mapped_doctors(self, tenant_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(func.distinct(MRDoctorMapping.doctor_id)))
            .where(MRDoctorMapping.tenant_id == tenant_id)
        )
        return int(result.scalar_one() or 0)

    async def _persona_mix(self, tenant_id: uuid.UUID) -> list[dict]:
        """Count distinct doctors per persona_tag for the tenant.

        Persona lives in core.doctor_ai_profile keyed by submission_id, so we
        join through core.submissions (which carries tenant_id + doctor_id).
        """
        result = await self.db.execute(
            select(
                DoctorAiProfile.persona_tag.label("persona"),
                func.count(func.distinct(Submission.doctor_id)).label("count"),
            )
            .select_from(Submission)
            .join(DoctorAiProfile, DoctorAiProfile.submission_id == Submission.id)
            .where(Submission.tenant_id == tenant_id)
            .where(DoctorAiProfile.persona_tag.is_not(None))
            .group_by(DoctorAiProfile.persona_tag)
        )
        counts = {row.persona: int(row.count) for row in result.all()}

        # Return in the canonical persona order, keeping any extra tags at the end.
        mix: list[dict] = []
        for persona in PERSONA_ORDER:
            mix.append({
                "persona": persona,
                "count": counts.pop(persona, 0),
                "color": PERSONA_COLORS.get(persona, "#94a3b8"),
            })
        for persona, count in counts.items():
            mix.append({"persona": persona, "count": count, "color": "#94a3b8"})
        return mix

    async def _brand_status(self, tenant_id: uuid.UUID) -> list[dict]:
        """Brand-engagement status distribution per brand for the Overview donuts.

        Source: ai.doctor_brand_engagement (status per doctor per brand),
        grouped by brand_name + status for the tenant.
        """
        result = await self.db.execute(
            select(
                DoctorBrandEngagement.brand_name.label("brand"),
                DoctorBrandEngagement.status.label("status"),
                func.count(DoctorBrandEngagement.id).label("count"),
            )
            .where(DoctorBrandEngagement.tenant_id == tenant_id)
            .where(DoctorBrandEngagement.brand_name.is_not(None))
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

    async def get_persona_strategy(self, tenant_id: uuid.UUID) -> dict:
        """Data for the Persona Mix -> "Strategy & Analytics" page.

        Combines:
          * persona counts (reuses the Overview persona mix)
          * behavioral opportunity tiers from ai.doctor_behavioral_profile
          * per-brand strategy narratives from ai.brand_strategy
        """
        persona_mix = await self._persona_mix(tenant_id)
        persona_total = sum(p["count"] for p in persona_mix)

        opportunity = await self._opportunity_tiers(tenant_id)
        strategies = await self._brand_strategies(tenant_id)

        return {
            "persona_mix": persona_mix,
            "persona_total": persona_total,
            "opportunity": opportunity,
            "strategies": strategies,
        }

    async def _opportunity_tiers(self, tenant_id: uuid.UUID) -> list[dict]:
        result = await self.db.execute(
            select(
                DoctorBehavioralProfile.opportunity_tier.label("tier"),
                func.count(DoctorBehavioralProfile.id).label("count"),
            )
            .where(DoctorBehavioralProfile.tenant_id == tenant_id)
            .where(DoctorBehavioralProfile.opportunity_tier.is_not(None))
            .group_by(DoctorBehavioralProfile.opportunity_tier)
        )
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

    async def _brand_strategies(self, tenant_id: uuid.UUID) -> list[dict]:
        result = await self.db.execute(
            select(BrandStrategy)
            .where(BrandStrategy.tenant_id == tenant_id)
            .order_by(BrandStrategy.brand_name)
        )
        rows = result.scalars().all()
        return [
            {
                "brand_name": r.brand_name,
                "strategy": r.strategy,
                "mr_approach": r.mr_approach,
            }
            for r in rows
        ]
