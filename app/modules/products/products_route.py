from math import ceil
import re
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
from app.modules.products.service.product_service import calculate_selling_price
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

    # -----------------------------
    # Filters
    # -----------------------------
    if filters.status:
        query["status"] = filters.status

    # -----------------------------
    # Search
    # -----------------------------
    if filters.searchText:
        search_text = filters.searchText.strip()

        if search_text:
            # Escape user input so special regex characters
            # don't change the query behavior.
            search_regex = re.escape(search_text)

            query["$or"] = [
                {"name": {"$regex": search_regex, "$options": "i"}},
                {"code": {"$regex": search_regex, "$options": "i"}},
                {"tags": {"$regex": search_regex, "$options": "i"}},
                {"categories": {"$regex": search_regex, "$options": "i"}},
            ]

    # -----------------------------
    # Pagination
    # -----------------------------
    page = max(filters.page, 1)
    page_size = max(filters.pageSize, 1)

    skip = (page - 1) * page_size

    # newest = descending
    # oldest = ascending
    sort_order = -1 if filters.sort == "newest" else 1

    # -----------------------------
    # Count AFTER applying filters
    # -----------------------------
    total = await collection.count_documents(query)

    # -----------------------------
    # Query MongoDB
    # Filtering happens in MongoDB BEFORE pagination
    # -----------------------------
    cursor = (
        collection.find(query)
        .sort("createdAt", sort_order)
        .skip(skip)
        .limit(page_size)
    )

    products = []

    async for doc in cursor:
        products.append(stringify_object_ids(doc))

    # -----------------------------
    # Response
    # -----------------------------
    return {
        "total": total,
        "page": page,
        "pageSize": page_size,
        "pages": ceil(total / page_size) if total > 0 else 1,
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
@router.post("", response_model=ProductOut, status_code=201)
async def create_product(payload: ProductIn, user=Depends(authenticate)):
    data = payload.model_dump()
    data["code"] = generate_product_code()
    data["price"]["sellingPrice"] = calculate_selling_price(data["price"])
    data["createdAt"] = datetime.now(timezone.utc)
    data["updatedAt"] = datetime.now(timezone.utc)
    data["createdBy"] = user.get("email")
    result = await collection.insert_one(data)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to insert order")

    data["id"] = str(result.inserted_id)
    return ProductOut(**data)

# ✅ Update a product (full replace)
@router.put("/{id}", response_model=ProductOut)
async def update_product(id: str, payload: ProductIn, user=Depends(authenticate)):
    data = payload.model_dump()
    data["price"]["sellingPrice"] = calculate_selling_price(data["price"])
    data["updatedAt"] = datetime.now(timezone.utc)
    data["updatedBy"] = user.get("email")
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
async def patch_product(id: str, payload: ProductUpdate, user=Depends(authenticate)):
    existing = await collection.find_one({"_id": ObjectId(id)})

    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    patch = payload.model_dump(exclude_unset=True)

    if "price" in patch:
        merged_price = {
            **existing.get("price", {}),
            **patch["price"],
        }

        if "discount" in patch["price"]:
            merged_price["discount"] = {
                **existing.get("price", {}).get("discount", {}),
                **patch["price"]["discount"],
            }

        if "tax" in patch["price"]:
            merged_price["tax"] = {
                **existing.get("price", {}).get("tax", {}),
                **patch["price"]["tax"],
            }

        merged_price["sellingPrice"] = calculate_selling_price(merged_price)
        patch["price"] = merged_price


    patch["updated_at"] = datetime.now(timezone.utc)
    patch["updatedBy"] = user.get("email")
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
async def delete_product(id: str, user=Depends(authenticate)):
    result = await collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {
            "status": "archived",
            "updatedAt": datetime.now(timezone.utc),
            "updatedBy": user.get("email")
            }
        }
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product archived"}