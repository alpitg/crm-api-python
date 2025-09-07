from math import ceil
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from datetime import datetime, timezone
from bson import ObjectId

from app.db.mongo import db
from app.modules.products.schemas.product import (
    GetProductsFilterIn,
    PaginatedProductsOut,
    ProductIn,
    ProductOut,
    ProductUpdate,
)
from app.utils.auth_utils import authenticate
from app.utils.generate_unique_id_util import generate_product_code
from core.sanitize import stringify_object_ids


# router = APIRouter(prefix="/api/products", tags=["products"])
router = APIRouter(
    dependencies=[Depends(authenticate)]  # ✅ applies to all routes
)
collection = db["products"]

# ✅ Get all products with pagination
@router.post("/search", response_model=PaginatedProductsOut)
async def list_products(filters: GetProductsFilterIn = Body(...)):
    query = {}
    # if filters.status:
    #     query["status"] = filters.status

    # Determine sort order
    sort_order = -1 if filters.sort == "newest" else 1  # newest = descending, oldest = ascending

    # Count total docs
    total = await collection.count_documents(query)

    # Apply pagination and sorting
    skip = (filters.page - 1) * filters.pageSize
    cursor = (
        collection.find(query)
        .sort("createdAt", sort_order)  # 👈 Sort by createdAt DESC
        .skip(skip)
        .limit(filters.pageSize)
    )

    products = []
    async for doc in cursor:
        if filters.searchText:
            ql = filters.searchText.lower()
            if not (
                (ql in doc.get("name", "").lower())
                or (ql in doc.get("code", "").lower())
                or any(ql in t.lower() for t in doc.get("tags", []))
                or any(ql in c.lower() for c in doc.get("categories", []))
            ):
                continue

        products.append(stringify_object_ids(doc))

    return {
        "total": total,
        "page": filters.page,
        "pageSize": filters.pageSize,
        "pages": ceil(total / filters.pageSize) if total > 0 else 1,
        "items": products,
    }


# ✅ Get product by id
@router.get("/{id}", response_model=ProductOut)
async def get_product(id: str):
    doc = await collection.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return doc

# ✅ Create new product
@router.post("/", response_model=ProductOut, status_code=201)
async def create_product(payload: ProductIn):
    data = payload.model_dump()
    data["code"] = generate_product_code()
    data["createdAt"] = datetime.now(timezone.utc)
    data["updatedAt"] = datetime.now(timezone.utc)
    result = await collection.insert_one(data)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to insert order")

    data["id"] = str(result.inserted_id)
    return ProductOut(**data)

# ✅ Update a product (full replace)
@router.put("/{id}", response_model=ProductOut)
async def update_product(id: str, payload: ProductIn):
    data = payload.model_dump()
    data["updated_at"] = datetime.now(timezone.utc)
    updated = await collection.find_one_and_update(
        {"_id": ObjectId(id)},
        {"$set": data},
        return_document=True
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Product not found")
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return ProductOut(**updated)

# ✅ Patch a product (partial update)
@router.patch("/{id}", response_model=ProductOut)
async def patch_product(id: str, payload: ProductUpdate):
    patch = payload.model_dump(exclude_unset=True)
    patch["updated_at"] = datetime.now(timezone.utc)
    updated = await collection.find_one_and_update(
        {"_id": ObjectId(id)},
        {"$set": patch},
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
        {"$set": {"status": "archived", "updated_at": datetime.now(timezone.utc)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product archived"}