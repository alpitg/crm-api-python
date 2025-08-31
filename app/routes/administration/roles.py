from datetime import datetime, timezone
from typing import List
from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException
from math import ceil
from app.schemas.administration.roles.roles import (
    GetRolesFilterIn,
    RoleIn,
    RoleOut,
    PaginatedRolesOut,
    RoleWithPermissions,
)
from app.utils.auth_utils import authenticate
from app.utils.generate_unique_id_util import generate_role_code
from core.sanitize import stringify_object_ids
from app.db.mongo import db

router = APIRouter(
    dependencies=[Depends(authenticate)]  # ✅ applies to all routes
)
collection = db["roles"]
role_permissions_collection = db["role_permissions"]


# ✅ Get All Roles with pagination ----------
@router.post("/search", response_model=PaginatedRolesOut)
async def list_roles(filters: GetRolesFilterIn = Body(...)):
    # Only fetch non-deleted roles
    query = {"$or": [{"isDeleted": {"$exists": False}}, {"isDeleted": False}]}

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
    query = {"$or": [{"isDeleted": {"$exists": False}}, {"isDeleted": False}]}

    cursor = collection.find(query)
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

# ---------- Get Role by ID ----------
@router.get("/{id}", response_model=RoleWithPermissions)
async def get_role(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid role ID")

    role = await collection.find_one({"_id": ObjectId(id), "isDeleted": False})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    role["id"] = str(role["_id"])

    return RoleWithPermissions(
        role=RoleOut(**stringify_object_ids(role)),
        grantedPermissionNames=role.get("grantedPermissionNames", [])
    )

# ✅ Create new Role with Permissions ----------
@router.post("/", response_model=RoleWithPermissions, status_code=201)
async def create_role(payload: RoleWithPermissions):
    role_data = payload.role.model_dump()
    role_data["name"] = role_data.get("displayName", None)
    role_data["code"] = generate_role_code(role_data["name"])
    role_data["isActive"] = True
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

    # ✅ ensure only one default role
    await ensure_single_default_role(role_data["id"], role_data.get("isDefault", False))

    # attach granted permissions
    role_with_permissions = RoleWithPermissions(
        role=RoleOut(**stringify_object_ids(role_data)),
        grantedPermissionNames=payload.grantedPermissionNames
    )

    return role_with_permissions

# ✅ Update Role with Permissions ----------
@router.put("/{id}", response_model=RoleOut)
async def update_role(id: str, payload: RoleWithPermissions):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid role ID")

    # Extract role fields + permissions
    role_data = payload.role.model_dump()
    role_data["grantedPermissionNames"] = payload.grantedPermissionNames
    role_data["lastModificationTime"] = datetime.now(timezone.utc)

    result = await collection.update_one(
        {"_id": ObjectId(id), "isDeleted": {"$ne": True}},
        {"$set": role_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Role not found")

    updated = await collection.find_one({"_id": ObjectId(id)})
    updated["id"] = str(updated["_id"])

    # ✅ ensure only one default role
    await ensure_single_default_role(id, role_data.get("isDefault", False))

    return RoleOut(**stringify_object_ids(updated))

# ✅ Delete Role ----------
@router.delete("/{id}", response_model=RoleOut)
async def delete_role(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid role ID")

    # First check if role exists
    role = await collection.find_one({"_id": ObjectId(id)})
    if not role or role.get("isDeleted"):
        raise HTTPException(status_code=404, detail="Role not found")

    # 🚫 Prevent deletion of static roles
    if role.get("isStatic", False):
        raise HTTPException(status_code=400, detail="Static roles cannot be deleted")

    # Soft delete (mark isDeleted=True)
    result = await collection.find_one_and_update(
        {"_id": ObjectId(id)},
        {
            "$set": {
                "isDeleted": True,
                "lastModificationTime": datetime.now(timezone.utc),
            }
        },
        return_document=True,
    )

    result["id"] = str(result["_id"])
    return RoleOut(**stringify_object_ids(result))

@router.post("/seed-default-roles", response_model=List[RoleOut], status_code=201)
async def seed_default_roles():
    """
    Ensure that Admin and User roles exist.
    If missing, create them with isStatic=True.
    """
    required_roles = [
        {"displayName": "Admin", "description": "Administrator role with full access", "code": "ADMIN"},
        {"displayName": "User", "description": "Default user role with limited access", "code": "USER"},
    ]

    created_or_existing = []

    for role_def in required_roles:
        existing = await collection.find_one({"code": role_def["code"], "isDeleted": False})
        
        if existing:
            # already exists
            role_out = RoleOut(**stringify_object_ids(existing))
            created_or_existing.append(role_out)
        else:
            # create new static role
            role_data = RoleIn(
                displayName=role_def["displayName"],
                description=role_def["description"],
                code=role_def["code"],
                isStatic=True,
                isActive=True
            ).model_dump()

            role_permissions = role_permissions_collection.find({}, {"name": 1, "_id": 0})
            permissions = []
            async for doc in role_permissions:
                if "name" in doc:
                    permissions.append(doc["name"])
                        
            role_data["name"] = role_data["displayName"]
            role_data["grantedPermissionNames"] = permissions
            role_data["creationTime"] = datetime.now(timezone.utc)
            role_data["lastModificationTime"] = None
            role_data["lastModifierUserId"] = None
            role_data["isDeleted"] = False

            result = await collection.insert_one(role_data)
            if not result.inserted_id:
                raise HTTPException(status_code=500, detail=f"Failed to create role {role_def['displayName']}")

            role_data["id"] = str(result.inserted_id)

            created_or_existing.append(RoleOut(**stringify_object_ids(role_data)))

    return created_or_existing


# private method
async def ensure_single_default_role(role_id: str, is_default: bool):
    """
    Ensure only one role has isDefault=True.
    If current role is default, set all others to False.
    """
    if is_default:
        # Set all roles' isDefault=False except the current one
        await collection.update_many(
            {"_id": {"$ne": ObjectId(role_id)}},
            {"$set": {"isDefault": False}}
        )
