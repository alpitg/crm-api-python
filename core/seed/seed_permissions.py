import json

from pathlib import Path
from app.db.mongo import db
from config import settings

role_permissions_collection = db["role_permissions"]

def flatten_permissions(data: dict) -> list:
    """
    Recursively flatten nested permission dictionaries into a flat list
    """
    flat_list = []

    def recurse(node: dict):

        # process current node if it's a permission object
        if "name" in node:

            flat_list.append(
                {
                    "name": node["name"],
                    "displayName": node.get("displayName"),
                    "description": node.get("description"),
                    "parentName": node.get("parentName"),
                    "isGrantedByDefault": node.get(
                        "isGrantedByDefault",
                        False
                    ),
                }
            )

        # go deeper for child permissions
        for key, value in node.items():

            if isinstance(value, dict):
                recurse(value)

    recurse(data)

    return flat_list


async def seed_role_permissions():

    """
    Reset role permissions.
    Delete existing permissions and insert fresh data from permissions.json.
    """
    print("🔄 Role permissions - Seeding role permissions...")

    # Ensure PROJECT_ROOT always has a valid value
    PROJECT_ROOT = (
        Path(settings.PROJECT_ROOT)
        if settings.PROJECT_ROOT
        else Path.cwd()
    )

    CONFIG_DIR = PROJECT_ROOT / "config"

    permissions_file = CONFIG_DIR / "permissions.json"

    if not permissions_file.exists():

        raise FileNotFoundError(
            f"Permissions file not found: {permissions_file}"
        )

    # Read JSON file
    with open(permissions_file, "r") as f:

        permission_json = json.load(f)

    # Flatten JSON into list
    flat_permissions = flatten_permissions(
        permission_json.get("PAGES", {})
    )

    # Clean existing permissions
    await role_permissions_collection.delete_many({})


    # Insert fresh permissions into MongoDB
    if flat_permissions:

        await role_permissions_collection.insert_many(
            flat_permissions
        )

    print("✅ Role permissions - seeded successfully with count: ", len(flat_permissions))

    return {
        "message": "Role permissions reset successfully",
        "count": len(flat_permissions)
    }
