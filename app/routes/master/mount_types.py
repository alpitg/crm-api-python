from fastapi import APIRouter, HTTPException
from typing import List
from bson import ObjectId
from app.db.mongo import db
from app.schemas.master.mount_type import MountTypeIn, MountTypeOut

router = APIRouter()
collection = db["master_mount_types"]

# ✅ Get all active mount types
@router.get("/", response_model=List[MountTypeOut])
async def get_all_mount_types():
    mounts = []
    cursor = collection.find({"is_active": True})
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        mounts.append(doc)
    return mounts

# ✅ Create a new mount type
@router.post("/", response_model=MountTypeOut)
async def create_mount_type(payload: MountTypeIn):
    data = payload.model_dump()
    result = await collection.insert_one(data)
    data["id"] = str(result.inserted_id)
    return MountTypeOut(**data)

# ✅ Update a mount type
@router.put("/{id}", response_model=MountTypeOut)
async def update_mount_type(id: str, payload: MountTypeIn):
    updated = await collection.find_one_and_update(
        {"_id": ObjectId(id)},
        {"$set": payload.model_dump()},
        return_document=True,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Mount type not found")
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return MountTypeOut(**updated)

# ✅ Soft-delete a mount type
@router.delete("/{id}")
async def delete_mount_type(id: str):
    result = await collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"is_active": False}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Mount type not found")
    return {"message": "Mount type soft-deleted"}
