from fastapi import APIRouter, HTTPException
from typing import List
from bson import ObjectId
from app.db.mongo import db
from app.schemas.master.order_status import OrderStatusIn, OrderStatusOut

router = APIRouter()
collection = db["master_order_status"]

# ✅ Get all active order statuses
@router.get("/", response_model=List[OrderStatusOut])
async def get_all_order_statuses():
    statuses = []
    cursor = collection.find({"is_active": True})
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        statuses.append(doc)
    return statuses

# ✅ Create a new order status
@router.post("/", response_model=OrderStatusOut)
async def create_order_status(payload: OrderStatusIn):
    data = payload.model_dump()
    result = await collection.insert_one(data)
    data["id"] = str(result.inserted_id)
    return OrderStatusOut(**data)

# ✅ Update an order status
@router.put("/{id}", response_model=OrderStatusOut)
async def update_order_status(id: str, payload: OrderStatusIn):
    updated = await collection.find_one_and_update(
        {"_id": ObjectId(id)},
        {"$set": payload.model_dump()},
        return_document=True,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Order status not found")
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return OrderStatusOut(**updated)

# ✅ Soft-delete an order status
@router.delete("/{id}")
async def delete_order_status(id: str):
    result = await collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"is_active": False}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order status not found")
    return {"message": "Order status soft-deleted"}
