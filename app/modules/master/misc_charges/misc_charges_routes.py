from fastapi import APIRouter, Depends, HTTPException
from typing import List
from bson import ObjectId
from app.db.mongo import db
from app.modules.master.misc_charges.schemas.misc_charge import MiscChargeIn, MiscChargeOut
from app.utils.auth_utils import authenticate

router = APIRouter(
    dependencies=[Depends(authenticate)]  # ✅ applies to all routes
)
collection = db["master_misc_charges"]

# ✅ Get all active misc charges
@router.get("/", response_model=List[MiscChargeOut])
async def get_all_misc_charges():
    charges = []
    cursor = collection.find({"is_active": True})
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        charges.append(doc)
    return charges

# ✅ Create a new misc charge
@router.post("/", response_model=MiscChargeOut)
async def create_misc_charge(payload: MiscChargeIn):
    data = payload.model_dump()
    result = await collection.insert_one(data)
    data["id"] = str(result.inserted_id)
    return MiscChargeOut(**data)

# ✅ Update a misc charge
@router.put("/{id}", response_model=MiscChargeOut)
async def update_misc_charge(id: str, payload: MiscChargeIn):
    updated = await collection.find_one_and_update(
        {"_id": ObjectId(id)},
        {"$set": payload.model_dump()},
        return_document=True,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Misc charge not found")
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return MiscChargeOut(**updated)

# ✅ Soft-delete a misc charge
@router.delete("/{id}")
async def delete_misc_charge(id: str):
    result = await collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"is_active": False}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Misc charge not found")
    return {"message": "Misc charge soft-deleted"}
