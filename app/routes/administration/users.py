from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Body, HTTPException
from math import ceil

from app.schemas.administration.users.users import (
    GetUsersFilterIn,
    UserOut,
    PaginatedUsersOut,
    UserPermission,
    UserWithPermissions,
)
from core.sanitize import stringify_object_ids
from app.db.mongo import db

router = APIRouter()
collection = db["users"]


# ✅ Get All Users with pagination ----------
@router.post("/search", response_model=PaginatedUsersOut)
async def list_users(filters: GetUsersFilterIn = Body(...)):
    # Only fetch non-deleted users
    query = {"$or": [{"isDeleted": {"$exists": False}}, {"isDeleted": False}]}

    # Apply search if provided
    if filters.searchText:
        regex = {"$regex": filters.searchText, "$options": "i"}
        query["$or"] = [
            {"userName": regex},
            {"name": regex},
            {"surname": regex},
            {"emailAddress": regex},
        ]

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

    users = []
    async for doc in cursor:
        users.append(stringify_object_ids(doc))

    return {
        "total": total,
        "page": filters.page,
        "pageSize": filters.pageSize,
        "pages": ceil(total / filters.pageSize) if total > 0 else 1,
        "items": users,
    }


# ✅ Get User by ID ----------
@router.get("/{id}", response_model=UserOut)
async def get_user(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user = await collection.find_one({"_id": ObjectId(id), "isDeleted": {"$ne": True}})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return stringify_object_ids(user)

# ✅ Create User ----------
@router.post("/", response_model=UserWithPermissions)
async def create_user(user_with_permissions: UserWithPermissions = Body(...)):
    now = datetime.now(timezone.utc)

    # prepare new user document without `id`
    new_user_doc = user_with_permissions.user.model_dump(exclude={"id"})
    new_user_doc["creationTime"] = now
    new_user_doc["lastModificationTime"] = None
    new_user_doc["lastModifierUserId"] = None
    new_user_doc["isDeleted"] = False

    # insert into MongoDB
    result = await collection.insert_one(new_user_doc)

    # add generated _id as id in response only
    new_user_doc["id"] = str(result.inserted_id)

    # build response
    return UserWithPermissions(
        user=UserOut(**new_user_doc),
        roles=user_with_permissions.roles,
        memberedOrganizationUnits=user_with_permissions.memberedOrganizationUnits,
        allOrganizationUnits=user_with_permissions.allOrganizationUnits,
        grantedPermissionNames=None,
        permissions=None,
    )


# ✅ Update User ----------
@router.put("/{id}", response_model=UserWithPermissions)
async def update_user(id: str, user_with_permissions: UserWithPermissions = Body(...)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    update_data = user_with_permissions.user.model_dump(exclude_unset=True)
    update_data["lastModificationTime"] = datetime.now(timezone.utc)

    result = await collection.find_one_and_update(
        {"_id": ObjectId(id), "isDeleted": {"$ne": True}},
        {"$set": update_data},
        return_document=True,
    )

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    # attach granted permissions
    user_with_permissions = UserWithPermissions(
        user=UserOut(**stringify_object_ids(update_data)),
        roles=user_with_permissions.roles,
        memberedOrganizationUnits=user_with_permissions.memberedOrganizationUnits,
        allOrganizationUnits=user_with_permissions.allOrganizationUnits,
        grantedPermissionNames= None,
        permissions= None
    )

    return user_with_permissions


# ✅ Soft Delete User ----------
@router.delete("/{id}", response_model=UserOut)
async def delete_user(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    result = await collection.find_one_and_update(
        {"_id": ObjectId(id), "isDeleted": {"$ne": True}},
        {
            "$set": {
                "isDeleted": True,
                "lastModificationTime": datetime.now(timezone.utc),
            }
        },
        return_document=True,
    )

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return stringify_object_ids(result)


# ✅ Update User Permissions ----------
@router.put("/{id}/permissions", response_model=UserPermission)
async def update_user_permissions(id: str, payload: UserPermission = Body(...)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    update_data = {
        "grantedPermissionNames": payload.grantedPermissionNames,
        "lastModificationTime": datetime.now(timezone.utc),
    }

    result = await collection.find_one_and_update(
        {"_id": ObjectId(id), "isDeleted": {"$ne": True}},
        {"$set": update_data},
        return_document=True,
    )

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    # Build response using UserPermission schema
    return UserPermission(
        id=str(result["_id"]),
        grantedPermissionNames=result.get("grantedPermissionNames", []),
    )