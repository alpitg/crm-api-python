from fastapi import APIRouter, HTTPException
from typing import List
from bson import ObjectId
from app.db.mongo import db
from app.schemas.customer import CustomerIn, CustomerOut

# Sample customer document structure in MongoDB
# {
#   "_id": "ObjectId",
#   "name": "John Doe",
#   "contact": {
#     "phone": "1234567890",
#     "email": "john@example.com"
#   },
#   "billingAddress": {
#     "street": "123 Main St",
#     "city": "Somewhere",
#     "state": "CA",
#     "postcode": "90210",
#     "country": "USA"
#   },
#   "is_active": true
# }


router = APIRouter()
collection = db["customers"]

# ✅ Get all active customers
@router.get("/", response_model=List[CustomerOut])
async def get_customers():
    customers = []
    cursor = collection.find({"is_active": True})
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        customers.append(doc)
    return customers

# ✅ Create a new customer
@router.post("/", response_model=CustomerOut)
async def create_customer(payload: CustomerIn):
    data = payload.model_dump()
    result = await collection.insert_one(data)
    data["id"] = str(result.inserted_id)
    return CustomerOut(**data)

# ✅ Update a customer
@router.put("/{id}", response_model=CustomerOut)
async def update_customer(id: str, payload: CustomerIn):
    updated = await collection.find_one_and_update(
        {"_id": ObjectId(id)},
        {"$set": payload.model_dump()},
        return_document=True
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Customer not found")
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return CustomerOut(**updated)

# ✅ Soft-delete a customer
@router.delete("/{id}")
async def delete_customer(id: str):
    result = await collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"is_active": False}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer soft-deleted"}
