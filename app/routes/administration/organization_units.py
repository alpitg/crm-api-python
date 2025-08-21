from datetime import datetime, timezone
from fastapi import APIRouter, Body, HTTPException
from math import ceil
from app.schemas.administration.organizationUnits.organization_units import GetOrganisationUnitsFilterIn, OrganisationUnitIn, OrganisationUnitOut, PaginatedOrganisationUnitsOut
from core.sanitize import stringify_object_ids
from app.db.mongo import db


# router = APIRouter(prefix="/api/organisation-units", tags=["organisation-units"])
router = APIRouter()
collection = db["organisation_units"]


# ✅ Get All Organisation Units ----------
@router.post("/search", response_model=PaginatedOrganisationUnitsOut)
async def list_organisation_units(filters: GetOrganisationUnitsFilterIn = Body(...)):
    query = {}

    # Determine sort order (using creationTime for now)
    sort_order = -1 if filters.sort == "newest" else 1

    # Count total docs
    total = await collection.count_documents(query)

    # Apply pagination and sorting
    skip = (filters.page - 1) * filters.pageSize
    cursor = (
        collection.find(query)
        .sort("creationTime", sort_order)
        .skip(skip)
        .limit(filters.pageSize)
    )

    organisation_units = []
    async for doc in cursor:
        if filters.searchText:
            ql = filters.searchText.lower()
            if not (
                (ql in (doc.get("displayName") or "").lower())
                or (ql in (doc.get("code") or "").lower())
            ):
                continue

        organisation_units.append(stringify_object_ids(doc))

    return {
        "total": total,
        "page": filters.page,
        "pageSize": filters.pageSize,
        "pages": ceil(total / filters.pageSize) if total > 0 else 1,
        "items": organisation_units,
    }

# ✅ Create new organisation unit
@router.post("/", response_model=OrganisationUnitOut, status_code=201)
async def create_organisation_unit(payload: OrganisationUnitIn):
    data = payload.model_dump()
    data["creationTime"] = datetime.now(timezone.utc)
    data["lastModificationTime"] = None
    data["lastModifierUserId"] = None

    result = await collection.insert_one(data)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create organisation unit")

    data["id"] = str(result.inserted_id)
    return OrganisationUnitOut(**stringify_object_ids(data))