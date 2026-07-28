from datetime import datetime, timezone

from app.db.mongo import db
from app.modules.administration.role.schemas.roles import RoleIn

collection = db["roles"]
role_permissions_collection = db["role_permissions"]

async def seed_default_roles():
    """
    Ensure that Admin and User roles exist.
    If missing, create them with isStatic=True.
    """

    required_roles = [
        {
            "displayName": "Admin",
            "description": "Administrator role with full access",
            "code": "ADMIN"
        },
        {
            "displayName": "User",
            "description": "Default user role with limited access",
            "code": "USER"
        },
    ]

    created_roles = []

    for role_def in required_roles:

        existing = await collection.find_one({
            "code": role_def["code"],
            "isDeleted": False
        })

        if existing:
            created_roles.append(existing)
            continue

        print("🔄 Roles - Seeding default roles...")

        role_data: RoleIn = {
            "name": role_def["displayName"],
            "displayName": role_def["displayName"],
            "description": role_def["description"],
            "code": role_def["code"],

            "isDefault": False,
            "isStatic": True,
            "isActive": True,
            "creatorUserId": None,
            "grantedPermissionNames": [],

            "creationTime": datetime.now(timezone.utc),
            "lastModificationTime": None,
            "lastModifierUserId": None,
            "isDeleted": False,
            "organisationUnitIds": []
        }

        role_permissions = role_permissions_collection.find(
            {},
            {"name": 1, "_id": 0}
        )

        permissions = []

        async for doc in role_permissions:
            if "name" in doc:
                permissions.append(doc["name"])

        role_data["grantedPermissionNames"] = permissions

        result = await collection.insert_one(role_data)

        if not result.inserted_id:
            raise Exception(
                f"Failed to create role {role_def['displayName']}"
            )


        role_data["id"] = str(result.inserted_id)

        created_roles.append(role_data)

        print("✅ Roles - Default roles seeded successfully.")

    return created_roles
