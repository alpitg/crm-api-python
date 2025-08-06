from fastapi import APIRouter, HTTPException
from typing import List
from bson import ObjectId
from app.db.mongo import db
from app.schemas.product import ProductIn, ProductOut

# {
#   "_id": ObjectId("..."),
#   "name": "Samsung 65\" QLED TV",
#   "description": "Ultra HD Smart QLED TV with Alexa Built-in",
#   "status": "active",
#   "inventory": 27,
#   "category": "Electronics",
#   "base_cost": 90000,
#   "mrp": 129999,
#   "price": 109999,
#   "totalWishlistedCount": 148,
#   "discount": {
#     "is_active": true,
#     "type": "percentage",     // or "flat"
#     "value": 15.38
#   },
#   "deal": {
#     "label": "Limited Time Deal",
#     "valid_till": "2025-08-07T23:59:59Z"
#   }
# }


router = APIRouter()
collection = db["products"]

# ✅ Get all active products
@router.get("/", response_model=List[ProductOut])
async def get_all_products():
    products = []
    cursor = collection.find({"status": "active"})
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        products.append(doc)
    return products

# ✅ Create new product
@router.post("/", response_model=ProductOut)
async def create_product(payload: ProductIn):
    data = payload.model_dump()
    result = await collection.insert_one(data)
    data["_id"] = str(result.inserted_id)
    return ProductOut(**data)

# ✅ Update a product
@router.put("/{id}", response_model=ProductOut)
async def update_product(id: str, payload: ProductIn):
    updated = await collection.find_one_and_update(
        {"_id": ObjectId(id)},
        {"$set": payload.model_dump()},
        return_document=True
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Product not found")
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return ProductOut(**updated)

# ✅ Soft delete a product
@router.delete("/{id}")
async def delete_product(id: str):
    result = await collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": "archived"}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product archived"}
