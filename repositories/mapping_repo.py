from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, delete, update
from sqlalchemy.orm import aliased
import uuid
from models.auth import Doctor, MRDoctorMapping, User
from schemas.mapping import MappingFilterParams
from models.submission import Submission

async def get_mappings_filtered(
    db: AsyncSession,
    tenant_id: str,
    filters: MappingFilterParams,
) -> tuple[list[dict], int]:
    MRUser = aliased(User, name="mr_user")
    ManagerUser = aliased(User, name="manager_user")

    base_query = (
        select(
            Doctor.id.label("doctor_id"),
            Doctor.name.label("doctor_name"),
            Doctor.area.label("area"),
            Doctor.state.label("state"),
            MRUser.id.label("mr_user_id"),
            MRUser.full_name.label("mr_name"),
            ManagerUser.full_name.label("manager_name"),
        )
        .select_from(Doctor)
        .outerjoin(
            MRDoctorMapping,
            (MRDoctorMapping.doctor_id == Doctor.id) & (MRDoctorMapping.tenant_id == Doctor.tenant_id)
        )
        .outerjoin(
            MRUser,
            (MRDoctorMapping.mr_id == MRUser.id)
        )
        .outerjoin(
            ManagerUser,
            (MRUser.reporting_to == ManagerUser.id)
        )
        .where(Doctor.tenant_id == tenant_id)
    )

    if filters.doctor_name:
        base_query = base_query.where(Doctor.name.ilike(f"%{filters.doctor_name}%"))
    if filters.mr_name:
        base_query = base_query.where(MRUser.full_name.ilike(f"%{filters.mr_name}%"))
    if filters.manager_name:
        base_query = base_query.where(ManagerUser.full_name.ilike(f"%{filters.manager_name}%"))

    # Subquery for count
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    offset = (filters.page - 1) * filters.page_size
    paginated = base_query.offset(offset).limit(filters.page_size)
    result = await db.execute(paginated)
    rows = result.all()

    # Convert to list of dicts that match the schema
    output = []
    for r in rows:
        location_parts = [p for p in [r.area, r.state] if p]
        geolocation = ", ".join(location_parts) if location_parts else None
        
        output.append({
            "id": str(r.doctor_id),
            "doctor_id": str(r.doctor_id),
            "doctor_name": r.doctor_name or "Unknown Doctor",
            "doctor_speciality": None,  # Data not easily available on Doctor model without joins
            "geolocation": geolocation,
            "mr_user_id": str(r.mr_user_id) if r.mr_user_id else None,
            "mr_name": r.mr_name,
            "manager_name": r.manager_name,
        })

    return output, total


async def get_all_filtered_doctor_ids(
    db: AsyncSession,
    tenant_id: str,
    filters: MappingFilterParams,
) -> list[str]:
    """
    Returns all doctor IDs matching the current filters (no pagination).
    Used by the Select All checkbox to select doctors across all pages.
    """
    MRUser = aliased(User, name="mr_user")
    ManagerUser = aliased(User, name="manager_user")

    query = (
        select(Doctor.id)
        .select_from(Doctor)
        .outerjoin(
            MRDoctorMapping,
            (MRDoctorMapping.doctor_id == Doctor.id) & (MRDoctorMapping.tenant_id == Doctor.tenant_id)
        )
        .outerjoin(MRUser, MRDoctorMapping.mr_id == MRUser.id)
        .outerjoin(ManagerUser, MRUser.reporting_to == ManagerUser.id)
        .where(Doctor.tenant_id == tenant_id)
    )

    if filters.doctor_name:
        query = query.where(Doctor.name.ilike(f"%{filters.doctor_name}%"))
    if filters.mr_name:
        query = query.where(MRUser.full_name.ilike(f"%{filters.mr_name}%"))
    if filters.manager_name:
        query = query.where(ManagerUser.full_name.ilike(f"%{filters.manager_name}%"))

    result = await db.execute(query)
    return [str(row[0]) for row in result.all()]



async def update_mapping_mr(
    db: AsyncSession,
    tenant_id: str,
    doctor_id: str,
    new_mr_user_id: str,
) -> tuple[str, str, str | None]:
    """
    Updates the mapping in the mr_doctor_mapping table.
    Returns (doctor_name, new_mr_name, new_manager_name).
    """
    doc_id = uuid.UUID(str(doctor_id))
    t_id = uuid.UUID(str(tenant_id))
    mr_uuid = uuid.UUID(str(new_mr_user_id))

    # Get the MR to get their name and manager
    mr_user = await db.execute(select(User).where(User.id == mr_uuid))
    mr = mr_user.scalar_one_or_none()
    if not mr:
        raise ValueError("Invalid MR user ID")

    new_mr_name = mr.full_name
    new_manager_name = None
    if mr.reporting_to:
        mgr = await db.execute(select(User).where(User.id == mr.reporting_to))
        mgr_user = mgr.scalar_one_or_none()
        if mgr_user:
            new_manager_name = mgr_user.full_name

    # Get Doctor
    doc_res = await db.execute(select(Doctor).where(Doctor.id == doc_id, Doctor.tenant_id == t_id))
    doctor = doc_res.scalar_one_or_none()
    if not doctor:
        raise ValueError("Doctor not found")
    doctor_name = doctor.name

    # Find existing mapping
    mapping_res = await db.execute(
        select(MRDoctorMapping)
        .where(MRDoctorMapping.doctor_id == doc_id, MRDoctorMapping.tenant_id == t_id)
    )
    mappings = mapping_res.scalars().all()

    if mappings:
        # Delete old mappings for this doctor
        await db.execute(
            delete(MRDoctorMapping)
            .where(MRDoctorMapping.doctor_id == doc_id)
            .where(MRDoctorMapping.tenant_id == t_id)
        )
    
    # Insert new mapping
    new_mapping = MRDoctorMapping(
        mr_id=mr_uuid,
        doctor_id=doc_id,
        tenant_id=t_id
    )
    db.add(new_mapping)

    # Transfer ownership of past submissions to the new MR
    await db.execute(
        update(Submission)
        .where(Submission.doctor_id == doc_id)
        .where(Submission.tenant_id == t_id)
        .values(submitted_by=mr_uuid)
    )

    await db.commit()
    return doctor_name, new_mr_name, new_manager_name


async def bulk_update_mapping_mr(
    db: AsyncSession,
    tenant_id: str,
    doctor_ids: list[str],
    new_mr_user_id: str,
) -> tuple[int, str]:
    """
    Atomically remap multiple doctors to a single MR.
    Returns (remapped_count, new_mr_name).
    If any part fails, the entire transaction rolls back.
    """
    t_id = uuid.UUID(str(tenant_id))
    mr_uuid = uuid.UUID(str(new_mr_user_id))
    doc_uuids = [uuid.UUID(str(d)) for d in doctor_ids]

    # Validate the new MR exists
    mr_res = await db.execute(select(User).where(User.id == mr_uuid))
    mr = mr_res.scalar_one_or_none()
    if not mr:
        raise ValueError("Invalid MR user ID")

    new_mr_name = mr.full_name

    # 1. Bulk delete old mappings for all selected doctors
    await db.execute(
        delete(MRDoctorMapping)
        .where(MRDoctorMapping.doctor_id.in_(doc_uuids))
        .where(MRDoctorMapping.tenant_id == t_id)
    )

    # 2. Bulk insert new mappings
    new_mappings = [
        MRDoctorMapping(mr_id=mr_uuid, doctor_id=d_id, tenant_id=t_id)
        for d_id in doc_uuids
    ]
    db.add_all(new_mappings)

    # 3. Bulk transfer ownership of past submissions to the new MR
    await db.execute(
        update(Submission)
        .where(Submission.doctor_id.in_(doc_uuids))
        .where(Submission.tenant_id == t_id)
        .values(submitted_by=mr_uuid)
    )

    # Atomic commit — all or nothing
    await db.commit()
    return len(doc_uuids), new_mr_name


async def get_mapping_filter_options(db: AsyncSession, tenant_id: str) -> dict:
    doc_res = await db.execute(select(Doctor.name).where(Doctor.tenant_id == tenant_id).distinct())
    doctors = sorted([d for d in doc_res.scalars().all() if d])
    
    mr_res = await db.execute(select(User.full_name).where(User.tenant_id == tenant_id, User.role == "MR").distinct())
    mrs = sorted([m for m in mr_res.scalars().all() if m])
    
    manager_query = select(User.full_name).where(
        User.tenant_id == tenant_id,
        User.id.in_(
            select(User.reporting_to).where(
                User.tenant_id == tenant_id, 
                User.role == "MR", 
                User.reporting_to.is_not(None)
            )
        )
    ).distinct()
    mgr_res = await db.execute(manager_query)
    managers = sorted([m for m in mgr_res.scalars().all() if m])
    
    return {
        "doctors": doctors,
        "mrs": mrs,
        "managers": managers
    }
