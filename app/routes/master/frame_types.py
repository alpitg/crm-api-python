from fastapi import APIRouter, Depends, HTTPException
from typing import List
from bson import ObjectId
from app.db.mongo import db
from app.schemas.master.frame_type import FrameTypeIn, FrameTypeOut
from app.utils.auth_utils import authenticate

router = APIRouter(
    dependencies=[Depends(authenticate)]  # ✅ applies to all routes
)
collection = db["master_frame_types"]

# ✅ Get all active frame types
@router.get("/", response_model=List[FrameTypeOut])
async def get_all_frame_types():
    frame_types = []
    cursor = collection.find({"is_active": True})
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        frame_types.append(doc)
    return frame_types

# ✅ Create a new frame type
@router.post("/", response_model=FrameTypeOut)
async def create_frame_type(payload: FrameTypeIn):
    data = payload.model_dump()
    result = await collection.insert_one(data)
    data["id"] = str(result.inserted_id)
    return FrameTypeOut(**data)

# ✅ Update a frame type
@router.put("/{id}", response_model=FrameTypeOut)
async def update_frame_type(id: str, payload: FrameTypeIn):
    updated = await collection.find_one_and_update(
        {"_id": ObjectId(id)},
        {"$set": payload.model_dump()},
        return_document=True,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Frame type not found")
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return FrameTypeOut(**updated)

# ✅ Soft-delete a frame type
@router.delete("/{id}")
async def delete_frame_type(id: str):
    result = await collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"is_active": False}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Frame type not found")
    return {"message": "Frame type soft-deleted"}
