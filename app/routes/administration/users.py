from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Body, HTTPException, Query
from math import ceil

from app.schemas.administration.users.users import (
    GetUsersFilterIn,
    UserOut,
    PaginatedUsersOut,
    UserPermission,
    UserWithPermissionsIn,
    UserWithPermissionsOut,
)
from app.services.roles_service import get_roles_by_ids
from app.services.users_service import get_user_with_permissions
from app.utils.auth_utils import generate_random_password, hash_password
from core.sanitize import sanitize_user, stringify_object_ids
from app.db.mongo import db

router = APIRouter()
collection = db["users"]
roles_collection = db["roles"]
org_units_collection = db["organisation_units"]


from math import ceil
from fastapi import Body, APIRouter

router = APIRouter()

# ✅ Get All Users with Pagination ----------
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

    # Determine sort order
    sort_order = -1 if filters.sort == "newest" else 1

    # Count total docs
    total = await collection.count_documents(query)

    # Apply pagination + exclude password at DB level
    skip = (filters.page - 1) * filters.pageSize
    cursor = (
        collection.find(query, projection={"password": 0, "tempPassword": 0})  # ✅ exclude password
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

# ✅ Create User ----------
@router.post("/create", response_model=UserWithPermissionsOut)
async def create_user(user_with_permissions: UserWithPermissionsIn = Body(...)):
    now = datetime.now(timezone.utc)

    new_user_doc = user_with_permissions.user.model_dump()
    new_user_doc["grantedRoles"] = user_with_permissions.grantedRoles or []
    new_user_doc["password"] = hash_password(new_user_doc["password"])
    new_user_doc["creationTime"] = now
    new_user_doc["lastModificationTime"] = None
    new_user_doc["lastModifierUserId"] = None
    new_user_doc["isDeleted"] = False

    result = await collection.insert_one(new_user_doc)
    new_user_doc["id"] = str(result.inserted_id)

    return UserWithPermissionsOut(
        user=UserOut(**new_user_doc),
        grantedRoles= await get_roles_by_ids(user_with_permissions.grantedRoles),
        roles=[],
        memberedOrganisationUnits=[],
        allOrganizationUnits=[],
        grantedPermissionNames=[],
        permissions=[],
    )

# ✅ Update User ----------
@router.put("/{id}", response_model=UserWithPermissionsOut)
async def update_user(id: str, user_with_permissions: UserWithPermissionsIn = Body(...)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    update_data = user_with_permissions.user.model_dump(exclude_unset=True)
    update_data["grantedRoles"] = user_with_permissions.grantedRoles or []
    update_data["lastModificationTime"] = datetime.now(timezone.utc)

    #region handle password separately

    password = update_data.get("password")
    set_random = update_data.get("setRandomPassword", False)

    if set_random:
        # Always override with random password
        random_password = generate_random_password()
        update_data["tempPassword"] = random_password
        update_data["password"] = hash_password(random_password)
        update_data["shouldChangePasswordOnNextLogin"] = True

    elif password:  # only hash if non-empty string
        update_data["password"] = hash_password(password)

    else:
        # if empty string or None, don't update password
        update_data.pop("password", None)

    #endregion

    result = await collection.find_one_and_update(
        {"_id": ObjectId(id), "isDeleted": {"$ne": True}},
        {"$set": update_data},
        return_document=True,
    )

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    update_data["id"] = id

    # remove password if present
    update_data = sanitize_user(update_data)

    # attach granted permissions
    user_with_permissions = UserWithPermissionsOut(
        user=UserOut(**stringify_object_ids(update_data)),
        grantedRoles= await get_roles_by_ids(user_with_permissions.grantedRoles),
        roles=user_with_permissions.roles,
        memberedOrganisationUnits=user_with_permissions.memberedOrganisationUnits,
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


# ✅ Get User by ID ----------
@router.get("/get-user-for-edit", response_model=UserWithPermissionsOut)
async def get_user(id: Optional[str] = Query(None)):
    return await get_user_with_permissions(id)
    

# ✅ Seed Admin User with All Roles ----------
@router.post("/seed-admin", response_model=dict)
async def seed_admin_user():
    """
    Creates a default Admin user if not already present.
    Assigns all available roles to grantedRoles.
    """

    admin_email = "admin@gmail.com"

    existing_admin = await collection.find_one({"emailAddress": admin_email})
    if existing_admin:
        return {
            "message": "Admin emailAddress already exists",
            "id": str(existing_admin["_id"]),
            "emailAddress": existing_admin["emailAddress"],
        }

    # Fetch all roles from roles collection
    roles_cursor = roles_collection.find({}, {"_id": 1})
    role_ids = [str(role["_id"]) async for role in roles_cursor]

    now = datetime.now(timezone.utc)

    admin_doc = {
        "userName": "admin",
        "name": "System",
        "surname": "Administrator",
        "emailAddress": admin_email,
        "isEmailConfirmed": True,
        "isActive": True,
        "phoneNumber": None,
        "profilePictureId": None,
        "lockoutEndDateUtc": None,
        "creationTime": now,
        "lastModificationTime": None,
        "lastModifierUserId": None,
        "isDeleted": False,
        "grantedRoles": role_ids,  # ✅ assign all roles
        "isDarkMode": False,
        "isLockoutEnabled": False,
        "sendActivationEmail": False,
        "setRandomPassword": False,
        "shouldChangePasswordOnNextLogin": False,
        "password": generate_random_password(),  # Set random password
    }

    result = await collection.insert_one(admin_doc)

    return {
        "message": "Admin user created successfully",
        "id": str(result.inserted_id),
        "userName": admin_doc["userName"],
        "grantedRoles": admin_doc["grantedRoles"],
    }

