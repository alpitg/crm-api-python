import json
from pathlib import Path
from fastapi import APIRouter, Depends
from typing import List

from app.schemas.administration.roles.role_permissions import RolePermissionOut
from app.utils.auth_utils import authenticate
from config import Settings
from core.sanitize import stringify_object_ids
from app.db.mongo import db

router = APIRouter(
    dependencies=[Depends(authenticate)]  # ✅ applies to all routes
)
collection = db["role_permissions"]


# ✅ 1. Get all role permissions
@router.get("/", response_model=List[RolePermissionOut])
async def get_role_permissions():
    cursor = collection.find({})
    results = []
    async for doc in cursor:
        results.append(stringify_object_ids(doc))
    return results


# ✅ 2. Reset role permissions (delete + insert fresh data)
@router.post("/reset", response_model=dict)
async def reset_role_permissions():
    settings = Settings()

    # ✅ Ensure PROJECT_ROOT always has a valid value
    PROJECT_ROOT = Path(settings.PROJECT_ROOT) if settings.PROJECT_ROOT else Path.cwd()
    CONFIG_DIR = PROJECT_ROOT / "config"
    permissions_file = CONFIG_DIR / "permissions.json"

    # Read JSON file
    with open(permissions_file, "r") as f:
        permission_json = json.load(f)

    # Flatten JSON into list
    flat_permissions = flatten_permissions(permission_json.get("PAGES", {}))

    # Clean existing permissions
    await collection.delete_many({})

    # Insert fresh permissions into MongoDB
    if flat_permissions:
        await collection.insert_many(flat_permissions)

    return {"message": "Role permissions reset successfully", "count": len(flat_permissions)}


def flatten_permissions(data: dict) -> list:
    """
    Recursively flatten nested permission dictionaries into a flat list
    """
    flat_list = []

    def recurse(node: dict):
        # process current node if it's a permission object
        if "name" in node:
            flat_list.append({
                "name": node["name"],
                "displayName": node.get("displayName"),
                "description": node.get("description"),
                "parentName": node.get("parentName"),
                "isGrantedByDefault": node.get("isGrantedByDefault", False),
            })

        # go deeper for child permissions
        for key, value in node.items():
            if isinstance(value, dict):
                recurse(value)

    recurse(data)
    return flat_list
