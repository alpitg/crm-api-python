from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.db.mongo import db
from core.sanitize import stringify_object_ids


wishlist_collection = db["wishlists"]
products_collection = db["products"]


class WishlistServiceError(Exception):
    pass


class WishlistService:
    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _identity_filter(
        self,
        customer_id: str | None = None,
        guest_cart_id: str | None = None,
    ) -> dict[str, Any]:
        if customer_id:
            return {
                "customerId": customer_id,
            }

        if guest_cart_id:
            return {
                "guestCartId": guest_cart_id,
            }

        raise WishlistServiceError(
            "Either customerId or guestCartId is required."
        )

    async def get_wishlist(
        self,
        customer_id: str | None = None,
        guest_cart_id: str | None = None,
    ) -> dict:
        identity = self._identity_filter(
            customer_id=customer_id,
            guest_cart_id=guest_cart_id,
        )

        wishlist = await wishlist_collection.find_one(identity)

        if not wishlist:
            now = self._now()

            wishlist = {
                **identity,
                "items": [],
                "createdAt": now,
                "updatedAt": now,
            }

            result = await wishlist_collection.insert_one(wishlist)

            wishlist["_id"] = result.inserted_id

        return stringify_object_ids(wishlist)

    async def add_item(
        self,
        product_id: str,
        customer_id: str | None = None,
        guest_cart_id: str | None = None,
    ) -> dict:
        identity = self._identity_filter(
            customer_id=customer_id,
            guest_cart_id=guest_cart_id,
        )

        product = await products_collection.find_one(
            {
                "_id": ObjectId(product_id),
            }
        )

        if not product:
            raise WishlistServiceError(
                "Product not found."
            )

        wishlist = await wishlist_collection.find_one(identity)

        now = self._now()

        if not wishlist:
            wishlist = {
                **identity,
                "items": [],
                "createdAt": now,
                "updatedAt": now,
            }

            result = await wishlist_collection.insert_one(wishlist)

            wishlist["_id"] = result.inserted_id

        existing_item = next(
            (
                item
                for item in wishlist.get("items", [])
                if item.get("productId") == product_id
            ),
            None,
        )

        if existing_item:
            return {
                "success": True,
                "message": "Product is already in wishlist.",
                "item": stringify_object_ids(existing_item),
            }

        item = {
            "_id": ObjectId(),
            "productId": product_id,
            **identity,
            "createdAt": now,
            "updatedAt": now,
        }

        await wishlist_collection.update_one(
            {
                "_id": wishlist["_id"],
            },
            {
                "$push": {
                    "items": item,
                },
                "$set": {
                    "updatedAt": now,
                },
            },
        )

        return {
            "success": True,
            "message": "Product added to wishlist.",
            "item": stringify_object_ids(item),
        }

    async def remove_item(
        self,
        product_id: str,
        customer_id: str | None = None,
        guest_cart_id: str | None = None,
    ) -> dict:
        identity = self._identity_filter(
            customer_id=customer_id,
            guest_cart_id=guest_cart_id,
        )

        wishlist = await wishlist_collection.find_one(identity)

        if not wishlist:
            return {
                "success": True,
                "message": "Product removed from wishlist.",
            }

        result = await wishlist_collection.update_one(
            {
                "_id": wishlist["_id"],
            },
            {
                "$pull": {
                    "items": {
                        "productId": product_id,
                    },
                },
                "$set": {
                    "updatedAt": self._now(),
                },
            },
        )

        if result.matched_count == 0:
            raise WishlistServiceError(
                "Wishlist not found."
            )

        return {
            "success": True,
            "message": "Product removed from wishlist.",
        }

    async def merge_guest_wishlist(
        self,
        guest_cart_id: str,
        customer_id: str,
    ) -> dict:
        if not guest_cart_id:
            raise WishlistServiceError(
                "Guest cart ID is required."
            )

        if not customer_id:
            raise WishlistServiceError(
                "Customer ID is required."
            )

        guest_wishlist = await wishlist_collection.find_one(
            {
                "guestCartId": guest_cart_id,
            }
        )

        if not guest_wishlist:
            customer_wishlist = await self.get_wishlist(
                customer_id=customer_id,
            )

            return {
                "success": True,
                "message": "No guest wishlist to merge.",
                "wishlist": customer_wishlist,
            }

        customer_wishlist = await wishlist_collection.find_one(
            {
                "customerId": customer_id,
            }
        )

        now = self._now()

        if not customer_wishlist:
            customer_wishlist = {
                "customerId": customer_id,
                "items": [],
                "createdAt": now,
                "updatedAt": now,
            }

            result = await wishlist_collection.insert_one(
                customer_wishlist
            )

            customer_wishlist["_id"] = result.inserted_id

        existing_product_ids = {
            item.get("productId")
            for item in customer_wishlist.get("items", [])
        }

        guest_items = guest_wishlist.get("items", [])

        items_to_add = []

        for item in guest_items:
            product_id = item.get("productId")

            if not product_id:
                continue

            if product_id in existing_product_ids:
                continue

            items_to_add.append(
                {
                    "_id": ObjectId(),
                    "productId": product_id,
                    "customerId": customer_id,
                    "createdAt": item.get("createdAt", now),
                    "updatedAt": now,
                }
            )

            existing_product_ids.add(product_id)

        if items_to_add:
            await wishlist_collection.update_one(
                {
                    "_id": customer_wishlist["_id"],
                },
                {
                    "$push": {
                        "items": {
                            "$each": items_to_add,
                        },
                    },
                    "$set": {
                        "updatedAt": now,
                    },
                },
            )

        await wishlist_collection.delete_one(
            {
                "_id": guest_wishlist["_id"],
            }
        )

        merged_wishlist = await wishlist_collection.find_one(
            {
                "_id": customer_wishlist["_id"],
            }
        )

        return {
            "success": True,
            "message": "Guest wishlist merged successfully.",
            "wishlist": stringify_object_ids(
                merged_wishlist or {}
            ),
        }


wishlist_service = WishlistService()