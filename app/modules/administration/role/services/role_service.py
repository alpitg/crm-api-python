from typing import List
from bson import ObjectId
from app.db.mongo import db
from app.modules.administration.role.schemas.roles import RoleOut

roles_collection = db["roles"]

async def get_roles_by_ids(role_ids: List[str]) -> List[RoleOut]:
    """
    Fetch roles from MongoDB by list of role_ids.
    """
    if not role_ids:
        return []

    # Convert string IDs to ObjectIds
    object_ids = [ObjectId(rid) for rid in role_ids if ObjectId.is_valid(rid)]

    cursor = roles_collection.find({"_id": {"$in": object_ids}})
    roles = []
    async for role in cursor:
        role["id"] = str(role["_id"])  # stringify ObjectId
        roles.append(role)

    return roles
