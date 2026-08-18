import math

from bson import ObjectId


class WebsiteOrderService:
    def __init__(self, orders_collection):
        self.orders_collection = orders_collection

    async def get_customer_orders(
        self,
        customer_id,
        page: int = 1,
        limit: int = 10,
    ):
        skip = (page - 1) * limit

        query = {
            "customerId": customer_id,
        }

        total = await self.orders_collection.count_documents(query)

        cursor = (
            self.orders_collection
            .find(query)
            .sort("createdAt", -1)
            .skip(skip)
            .limit(limit)
        )

        orders = await cursor.to_list(length=limit)

        return {
            "orders": orders,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total else 0,
        }