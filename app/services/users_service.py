from typing import Optional
from bson import ObjectId
from app.db.mongo import db
from app.schemas.administration.organisation_units.organisation_units import OrganisationUnitOut
from app.schemas.administration.users.users import UserOut, UserWithPermissionsOut
from app.schemas.administration.roles.roles import RoleOut
from core.sanitize import stringify_object_ids

# Collections
users_collection = db["users"]
roles_collection = db["roles"]
org_units_collection = db["organisation_units"]


async def get_user_with_permissions(id: Optional[str]) -> UserWithPermissionsOut:
    user_doc = None

    # ---------- Try fetching user only if valid ObjectId ----------
    if id and ObjectId.is_valid(id):
        user_doc = await users_collection.find_one(
            {"_id": ObjectId(id), "isDeleted": {"$ne": True}}
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

    async for role_doc in roles_cursor:
        role_doc = stringify_object_ids(role_doc)

        # check assignment based on grantedRoles (list of roleIds)
        is_assigned = False
        if user_doc and "grantedRoles" in user_doc:
            is_assigned = role_doc["id"] in user_doc.get("grantedRoles", [])

        all_roles.append(
            RoleOut(
                **role_doc,
                isAssigned=is_assigned,
                inheritedFromOrganizationUnit=False,
            )
        )

    # ---------- fetch all org units ----------
    org_units_cursor = org_units_collection.find(
        {"$or": [{"isDeleted": {"$exists": False}}, {"isDeleted": False}]}
    )
    all_org_units: list[OrganisationUnitOut] = []
    async for ou_doc in org_units_cursor:
        all_org_units.append(OrganisationUnitOut(**stringify_object_ids(ou_doc)))

    # ---------- response ----------
    return UserWithPermissionsOut(
        user=user_out,
        roles=all_roles,
        memberedOrganisationUnits=user_doc.get("memberedOrganisationUnits", []) if user_doc else [],
        allOrganizationUnits=all_org_units,
        grantedPermissionNames=user_doc.get("grantedPermissionNames", []) if user_doc else [],
        permissions=user_doc.get("permissions", []) if user_doc else [],
    )
