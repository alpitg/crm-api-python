from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException
from math import ceil
from app.modules.administration.organisation_units.schemas.organisation_units import AddRolesToOrganisationUnitIn, DeleteRolesToOrganisationUnitIn, GetOrganisationUnitsFilterIn, GetOrganizationUnitsParamsAssignRole, OrganisationUnitIn, OrganisationUnitOut, PaginatedOrganisationUnitsOut
from app.modules.administration.role.schemas.roles import PaginatedRolesOut
from app.utils.auth_utils import authenticate
from core.sanitize import stringify_object_ids
from app.db.mongo import db


# router = APIRouter(prefix="/api/organisation-units", tags=["organisation-units"])
router = APIRouter(
    dependencies=[Depends(authenticate)]  # ✅ applies to all routes
)
collection = db["organisation_units"]
roles_collection = db["roles"]

from bson import ObjectId

# ✅ Get All Organisation Units with pagination ----------
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
        # Filter by search text
        if filters.searchText:
            ql = filters.searchText.lower()
            if not (
                (ql in (doc.get("displayName") or "").lower())
                or (ql in (doc.get("code") or "").lower())
            ):
                continue

        # ✅ Compute roleCount for this org unit
        org_unit_id = str(doc["_id"])
        role_count = await roles_collection.count_documents(
            {"organisationUnitIds": org_unit_id, "isDeleted": {"$ne": True}}
        )

        # Add roleCount to doc
        doc["roleCount"] = role_count

        organisation_units.append(stringify_object_ids(doc))

    return {
        "total": total,
        "page": filters.page,
        "pageSize": filters.pageSize,
        "pages": ceil(total / filters.pageSize) if total > 0 else 1,
        "items": organisation_units,
    }

# ✅ Get All Organisation Units ----------
@router.get("/", response_model=PaginatedOrganisationUnitsOut)
async def list_organisation_units():
    """
    Get all organisation units with their roleCount.
    """
    cursor = collection.find({})
    organisation_units = []

    async for doc in cursor:
        org_unit_id = str(doc["_id"])

        # ✅ Count how many roles reference this org unit
        role_count = await roles_collection.count_documents(
            {"organisationUnitIds": org_unit_id, "isDeleted": {"$ne": True}}
        )

        doc["roleCount"] = role_count  # attach the roleCount to the doc
        organisation_units.append(stringify_object_ids(doc))

    total = len(organisation_units)

    return {
        "total": total,
        "page": 1,              # static for GET-all
        "pageSize": total,      # returning all
        "pages": ceil(total / total) if total > 0 else 1,
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


# ✅ List roles with assignment status for a specific organisation unit
@router.post("/{org_unit_id}/roles/search", response_model=PaginatedRolesOut)
async def list_roles_for_org_unit(
    org_unit_id: str, filters: GetOrganizationUnitsParamsAssignRole = Body(...)
):
    if not ObjectId.is_valid(org_unit_id):
        raise HTTPException(status_code=400, detail="Invalid organisation unit ID")

    # Base query: non-deleted roles
    query = {"$or": [{"isDeleted": {"$exists": False}}, {"isDeleted": False}]}

    # Apply isAssigned filter
    if filters.isAssigned is True:
        # Only roles assigned to this org unit
        query["organisationUnitIds"] = org_unit_id
    elif filters.isAssigned is False:
        # Only roles NOT assigned to this org unit
        query["$or"] = [
            {"organisationUnitIds": {"$exists": False}},
            {"organisationUnitIds": {"$nin": [org_unit_id]}},
        ]
    # else None => return all roles regardless of assignment

    # Determine sort order
    sort_order = -1 if filters.sort == "newest" else 1

    # Count total matching documents
    total = await roles_collection.count_documents(query)

    # Pagination
    skip = (filters.page - 1) * filters.pageSize
    cursor = (
        roles_collection.find(query)
        .sort("creationTime", sort_order)
        .skip(skip)
        .limit(filters.pageSize)
    )

    roles = []
    async for doc in cursor:
        # Apply searchText filtering
        if filters.searchText:
            ql = filters.searchText.lower()
            if not (
                (ql in (doc.get("name") or "").lower())
                or (ql in (doc.get("displayName") or "").lower())
            ):
                continue
        roles.append(stringify_object_ids(doc))

    return {
        "total": total,
        "page": filters.page,
        "pageSize": filters.pageSize,
        "pages": ceil(total / filters.pageSize) if total > 0 else 1,
        "items": roles,
    }


# ✅ Add (tag) multiple roles to an organisation unit
@router.post("/roles/add")
async def add_roles_to_organisation_unit(payload: AddRolesToOrganisationUnitIn = Body(...)):
    org_unit_id = payload.organizationUnitId
    role_ids = payload.roleIds

    if not ObjectId.is_valid(org_unit_id):
        raise HTTPException(status_code=400, detail="Invalid organisation unit id")

    # Validate all role ids
    invalid_roles = [rid for rid in role_ids if not ObjectId.is_valid(rid)]
    if invalid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role ids: {invalid_roles}")

    updated_roles = []
    for rid in role_ids:
        result = await roles_collection.update_one(
            {"_id": ObjectId(rid)},
            {
                # push org_unit_id to array only if not already present
                "$addToSet": {"organisationUnitIds": org_unit_id},
                "$set": {"lastModificationTime": datetime.now(timezone.utc)},
            },
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"Role {rid} not found")

        role_doc = await roles_collection.find_one({"_id": ObjectId(rid)})
        updated_roles.append(stringify_object_ids(role_doc))

    return {
        "success": True,
        "message": f"Roles successfully tagged to organisation unit",
        "items": updated_roles
    }


# ✅ Remove (untag) a single role from an organisation unit
@router.post("/roles/remove")
async def remove_role_from_organisation_unit(payload: DeleteRolesToOrganisationUnitIn = Body(...)):
    """Remove a single role from an organisation unit"""
    if not ObjectId.is_valid(payload.roleId):
        raise HTTPException(status_code=400, detail="Invalid RoleId")
    if not ObjectId.is_valid(payload.organizationUnitId):
        raise HTTPException(status_code=400, detail="Invalid OrganizationUnitId")

    result = await roles_collection.update_one(
        {"_id": ObjectId(payload.roleId)},
        {
            "$pull": {"organisationUnitIds": payload.organizationUnitId},
            "$set": {"lastModificationTime": datetime.now(timezone.utc)},
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Role not found")

    doc = await roles_collection.find_one({"_id": ObjectId(payload.roleId)})
    return  {
        "success": True,
        "message": f"Roles successfully removed from organisation unit",
        "items": []
    }