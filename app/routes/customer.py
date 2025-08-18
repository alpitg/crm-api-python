from math import ceil
from fastapi import APIRouter, Body, HTTPException, Query
from uuid import uuid4
from datetime import datetime, timezone
from app.db.mongo import db
from app.schemas.customer import CustomerIn, CustomerOut, GetCustomersParams, PaginatedCustomers

router = APIRouter()
collection = db["customers"]

@router.post("/search", response_model=dict)
async def search_customers(filters: GetCustomersParams = Body(...)):
    skip = (filters.page - 1) * filters.pageSize

    # Build query dynamically
    query = {}
    if filters.searchText:
        query["name"] = {"$regex": filters.searchText, "$options": "i"}
    if filters.status:
        query["isActive"] = filters.status.lower() == "active"

    # Determine sort order
    sort_order = -1 if filters.sort == "newest" else 1  # newest = descending, oldest = ascending


    # Count total
    total_customers = await collection.count_documents(query)

    customers_summary = []
    cursor = (
        collection
        .find(query)
        .sort("createdAt", sort_order)
        .skip(skip)
        .limit(filters.pageSize)
    )

    async for customer in cursor:
        customers_summary.append(
            CustomerOut(
                id=str(customer["_id"]),
                name=customer.get("name", ""),
                email=customer.get("email", ""),
                description=customer.get("description", ""),
                addresses=customer.get("addresses", []),
                shippingAddress=customer.get("shippingAddress"),
                billingAddress=customer.get("billingAddress"),
                isActive=customer.get("isActive", True),
                createdAt=customer.get("createdAt"),
                updatedAt=customer.get("updatedAt"),
            )
        )

    return {
        "total": total_customers,
        "page": filters.page,
        "pageSize": filters.pageSize,
        "pages": ceil(total_customers / filters.pageSize) if total_customers > 0 else 1,
        "items": customers_summary
    }

@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(customer_id: str):
    customer = await collection.find_one({"id": customer_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.post("/", response_model=CustomerOut)
async def create_customer(payload: CustomerIn):
    now = datetime.now(timezone.utc)
    customer = {
        "id": str(uuid4()),
        "name": payload.name,
        "email": payload.email,
        "description": payload.description,
        "addresses": [addr.model_dump() for addr in payload.addresses],
        "shippingAddress": payload.shippingAddress.model_dump() if payload.shippingAddress else None,
        "billingAddress": payload.billingAddress.model_dump() if payload.billingAddress else None,
        "isActive": payload.isActive,
        "createdAt": now,
        "updatedAt": now,
    }
    await collection.insert_one(customer)
    return customer

@router.put("/{customer_id}", response_model=CustomerOut)
async def update_customer(customer_id: str, payload: CustomerIn):
    customer = await collection.find_one({"id": customer_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    updated_data = {
        **payload.model_dump(),
        "updatedAt": datetime.now(timezone.utc)
    }

    await collection.update_one({"id": customer_id}, {"$set": updated_data})
    updated_customer = await collection.find_one({"id": customer_id})
    return updated_customer

@router.delete("/{customer_id}")
async def delete_customer(customer_id: str):
    result = await collection.delete_one({"id": customer_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted successfully"}
