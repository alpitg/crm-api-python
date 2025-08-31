from fastapi import APIRouter, Depends, HTTPException
from typing import List
from bson import ObjectId
from app.db.mongo import db
from app.schemas.master.glass_type import GlassTypeIn, GlassTypeOut
from app.utils.auth_utils import authenticate

router = APIRouter(
    dependencies=[Depends(authenticate)]  # ✅ applies to all routes
)
collection = db["master_glass_types"]

# ✅ Get all active glass types
@router.get("/", response_model=List[GlassTypeOut])
async def get_all_glass_types():
    glass_types = []
    cursor = collection.find({"is_active": True})
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        glass_types.append(doc)
    return glass_types

# ✅ Create a new glass type
@router.post("/", response_model=GlassTypeOut)
async def create_glass_type(payload: GlassTypeIn):
    data = payload.model_dump()
    result = await collection.insert_one(data)
    data["id"] = str(result.inserted_id)
    return GlassTypeOut(**data)

# ✅ Update a glass type
@router.put("/{id}", response_model=GlassTypeOut)
async def update_glass_type(id: str, payload: GlassTypeIn):
    updated = await collection.find_one_and_update(
        {"_id": ObjectId(id)},
        {"$set": payload.model_dump()},
        return_document=True,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Glass type not found")
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return GlassTypeOut(**updated)

# ✅ Soft-delete a glass type
@router.delete("/{id}")
async def delete_glass_type(id: str):
    result = await collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"is_active": False}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Glass type not found")
    return {"message": "Glass type soft-deleted"}
