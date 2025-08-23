from datetime import datetime, timezone
from fastapi import APIRouter, Body, HTTPException
from math import ceil
from app.schemas.administration.roles.roles import (
    GetRolesFilterIn,
    RoleIn,
    RoleOut,
    PaginatedRolesOut,
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


# ✅ Create new Role ----------
@router.post("/", response_model=RoleOut, status_code=201)
async def create_role(payload: RoleIn):
    data = payload.model_dump()
    data["creationTime"] = datetime.now(timezone.utc)
    data["lastModificationTime"] = None
    data["lastModifierUserId"] = None
    data["isDeleted"] = False

    result = await collection.insert_one(data)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create role")

    data["id"] = str(result.inserted_id)
    return RoleOut(**stringify_object_ids(data))
