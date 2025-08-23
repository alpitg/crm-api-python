from datetime import datetime, timezone
from fastapi import APIRouter, Body, HTTPException
from math import ceil
from app.schemas.administration.roles.roles import (
    GetRolesFilterIn,
    RoleIn,
    RoleOut,
    PaginatedRolesOut,
    RoleWithPermissions,
)
from core.sanitize import stringify_object_ids
from app.db.mongo import db

router = APIRouter()
collection = db["roles"]


# ✅ Get All Roles with pagination ----------
@router.post("/search", response_model=PaginatedRolesOut)
async def list_roles(filters: GetRolesFilterIn = Body(...)):
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

    roles = []
    async for doc in cursor:
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


# ✅ Get All Roles ----------
@router.get("/", response_model=PaginatedRolesOut)
async def list_roles_all():
    cursor = collection.find({})
    roles = []
    async for doc in cursor:
        roles.append(stringify_object_ids(doc))

    return {
        "total": len(roles),
        "page": 1,
        "pageSize": len(roles),
        "pages": 1,
        "items": roles,
    }

# ✅ Create new Role with Permissions ----------
@router.post("/", response_model=RoleWithPermissions, status_code=201)
async def create_role(payload: RoleWithPermissions):
    role_data = payload.role.model_dump()
    role_data["name"] = role_data.get("displayName", None)
    role_data["creationTime"] = datetime.now(timezone.utc)
    role_data["lastModificationTime"] = None
    role_data["lastModifierUserId"] = None
    role_data["isDeleted"] = False

    # store permissions along with role
    role_data["grantedPermissionNames"] = payload.grantedPermissionNames

    # insert role
    result = await collection.insert_one(role_data)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create role")

    role_data["id"] = str(result.inserted_id)

    # attach granted permissions
    role_with_permissions = RoleWithPermissions(
        role=RoleOut(**stringify_object_ids(role_data)),
        grantedPermissionNames=payload.grantedPermissionNames
    )

    return role_with_permissions