from datetime import datetime, timezone

from app.db.mongo import db
from app.utils.auth_utils import generate_random_password

collection = db["users"]
roles_collection = db["roles"]

async def seed_admin_user():

    """
    Creates a default Admin user if not already present.
    Assigns all available roles to grantedRoles.
    """

    admin_email = "administrator@crm.local"

    existing_admin = await collection.find_one({
        "emailAddress": admin_email
    })

    if existing_admin:

        return {
            "message": "Admin emailAddress already exists",
            "id": str(existing_admin["_id"]),
            "emailAddress": existing_admin["emailAddress"],
        }

    print("🔄 Seeding admin user...")
    

    # Fetch all roles from roles collection
    roles_cursor = roles_collection.find(
        {},
        {
            "_id": 1
        }
    )

    role_ids = [
        str(role["_id"])
        async for role in roles_cursor
    ]

    now = datetime.now(timezone.utc)

    admin_doc = {
        "userName": "administrator",
        "name": "System",
        "surname": "Administrator",
        "emailAddress": admin_email,
        "isEmailConfirmed": True,
        "gender": None,
        "isActive": True,
        "phoneNumber": None,
        "profilePictureId": None,
        "lockoutEndDateUtc": None,
        "creationTime": now,
        "lastModificationTime": None,
        "lastModifierUserId": None,
        "isDeleted": False,
        "grantedRoles": role_ids,
        "isDarkMode": False,
        "isLockoutEnabled": False,
        "sendActivationEmail": False,
        "setRandomPassword": True,
        "shouldChangePasswordOnNextLogin": True,
        "password": generate_random_password(),
    }

    result = await collection.insert_one(admin_doc)

    print("✅ Admin user seeded successfully with email: ", admin_email)

    return {
        "message": "Admin user created successfully",
        "id": str(result.inserted_id),
        "userName": admin_doc["userName"],
        "emailAddress": admin_doc["emailAddress"],
        "grantedRoles": admin_doc["grantedRoles"],
    }
