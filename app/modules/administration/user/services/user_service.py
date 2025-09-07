from typing import Optional
from bson import ObjectId
from fastapi import HTTPException
from app.db.mongo import db
from app.modules.administration.organisation_units.schemas.organisation_units import OrganisationUnitOut
from app.modules.administration.user.schemas.users import UserIn, UserOut, UserWithPermissionsOut
from app.modules.administration.role.schemas.roles import RoleOut
from app.utils.auth_utils import generate_random_password, hash_password
from core.sanitize import sanitize_user, stringify_object_ids
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId
from typing import Optional


# Collections
users_collection = db["users"]
roles_collection = db["roles"]
org_units_collection = db["organisation_units"]


def handle_password_logic(user_data: UserIn, is_update: bool = False) -> UserIn:
    """
    Handle password logic for both add and update cases.
    - On create: ensures password is set if provided, or can generate random.
    - On update: hashes only if provided or setRandomPassword is True.
    """

    update_data = dict(user_data)  # ✅ safe dict copy

    password: Optional[str] = update_data.get("password")
    set_random: bool = update_data.get("setRandomPassword", False)

    if set_random:
        # Always override with random password
        random_password = generate_random_password()
        update_data["tempPassword"] = random_password
        update_data["password"] = hash_password(random_password)
        update_data["shouldChangePasswordOnNextLogin"] = True

    elif password:
        # Hash password if provided
        update_data["password"] = hash_password(password)

    else:
        # In update mode, don’t overwrite password if not provided
        if is_update:
            update_data.pop("password", None)
        else:
            # In create mode, allow empty password only if setRandomPassword is True
            update_data.pop("password", None)

    return update_data


async def ensure_unique_user(
    collection: AsyncIOMotorCollection, 
    user_data: dict, 
    exclude_id: str | None = None
):
    """
    Ensure username or email is unique.
    If exclude_id is given, skip that document during update.
    """
    query = {
        "$or": [
            {"userName": user_data["userName"]},
            {"emailAddress": user_data["emailAddress"]}
        ]
    }

    if exclude_id and ObjectId.is_valid(exclude_id):
        query["$and"] = [{"_id": {"$ne": ObjectId(exclude_id)}}]

    existing_user = await collection.find_one(query)

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username or Email already exists"
        )


async def get_user_with_permissions(id: Optional[str]) -> UserWithPermissionsOut:
    user_doc = None

    # ---------- Try fetching user only if valid ObjectId ----------
    if id and ObjectId.is_valid(id):
        user_doc = await users_collection.find_one(
            {"_id": ObjectId(id), "isDeleted": {"$ne": True}},
            projection={"password": 0, "tempPassword": 0}
        )
        if user_doc:
            user_doc = stringify_object_ids(user_doc)

    # ---------- prepare user_out ----------
    if user_doc:
        user_out = UserOut(**user_doc)
    else:
        # Create empty object with default values
        user_out = UserOut(
            id="",
            userName="",
            name="",
            surname="",
            emailAddress="",
            password="",
            isActive=False,
            fullName="",
            creationTime=None,
            lastModificationTime=None,
            lastModifierUserId=None,
            isDeleted=False,
        )

    # ---------- fetch all roles ----------
    roles_cursor = roles_collection.find(
        {"$or": [{"isDeleted": {"$exists": False}}, {"isDeleted": False}]}
    )
    all_roles: list[RoleOut] = []
    grantedRoles: list[RoleOut] = []

    async for role_doc in roles_cursor:
        role_doc = stringify_object_ids(role_doc)

        # check assignment based on grantedRoles (list of roleIds)
        is_assigned = False
        if user_doc and "grantedRoles" in user_doc:
            is_assigned = role_doc["id"] in user_doc.get("grantedRoles", [])

        role_out = RoleOut(
                **role_doc,
                isAssigned=is_assigned,
                inheritedFromOrganizationUnit=False,
            )

        if is_assigned:
            grantedRoles.append(role_out)
        all_roles.append(role_out)


    # ---------- fetch all org units ----------
    org_units_cursor = org_units_collection.find(
        {"$or": [{"isDeleted": {"$exists": False}}, {"isDeleted": False}]}
    )
    all_org_units: list[OrganisationUnitOut] = []
    async for ou_doc in org_units_cursor:
        all_org_units.append(OrganisationUnitOut(**stringify_object_ids(ou_doc)))

    # remove password if present
    user_out = sanitize_user(user_out)

    # ---------- response ----------
    return UserWithPermissionsOut(
        user=user_out,
        roles=all_roles,
        grantedRoles=grantedRoles,
        memberedOrganisationUnits=user_doc.get("memberedOrganisationUnits", []) if user_doc else [],
        allOrganizationUnits=all_org_units,
        grantedPermissionNames=user_doc.get("grantedPermissionNames", []) if user_doc else [],
        permissions=user_doc.get("permissions", []) if user_doc else [],
    )
