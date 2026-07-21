from math import ceil
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from app.db.mongo import db

from app.modules.products.public.product_public_schema import (
    PaginatedProductsOut,
    PublicProductOut,
)

public_router = APIRouter()

collection = db["products"]

@public_router.get(
    "/products",
    response_model=PaginatedProductsOut
)
async def search_products(
    search: str | None = None,
    category: str | None = None,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=50),
):

    query = {
        "status": "published"
    }

    if search:
        query["$or"] = [
            {
                "name": {
                    "$regex": search,
                    "$options": "i"
                }
            },
            {
                "tags": {
                    "$regex": search,
                    "$options": "i"
                }
            },
            {
                "categories": {
                    "$regex": search,
                    "$options": "i"
                }
            }
        ]

    if category:
        query["categories"] = category

    # total count
    total = await collection.count_documents(query)

    cursor = (
        collection
        .find(query)
        .skip((page - 1) * pageSize)
        .limit(pageSize)
    )

    items = []

    async for item in cursor:
        price = item.get("price", {})

        items.append(
            {
                "id": str(item["_id"]),
                "name": item.get("name"),
                "description": item.get("description"),
                "categories": item.get("categories", []),
                "tags": item.get("tags", []),
                "media": item.get("media", []),
                "price": item.get("price"),
                "status": item.get("status")
            }
        )

    return {
        "total": total,
        "page": page,
        "pageSize": pageSize,
        "pages": ceil(total / pageSize) if total else 1,
        "items": items
    }


@public_router.get(
    "/products/{id}",
    response_model=PublicProductOut
)
async def get_public_product(id: str):

    try:
        object_id = ObjectId(id)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid product id"
        )

    product = await collection.find_one(
        {
            "_id": object_id,
            "status": "published"
        }
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    price = product.get("price", {})

    return {
        "id": str(product["_id"]),
        "name": product.get("name"),
        "description": product.get("description"),
        "categories": product.get(
            "categories",
            []
        ),
        "tags": product.get(
            "tags",
            []
        ),
        "media": product.get(
            "media",
            []
        ),
        "price": {
            "basePrice": price.get("basePrice"),
            "sellingPrice": (
                price.get("sellingPrice")
                if price.get("sellingPrice") is not None
                else price.get("basePrice")
            ),
            "currency": "INR"
        },
        "status": product.get("status")
    }