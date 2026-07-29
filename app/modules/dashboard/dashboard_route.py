from typing import List
from fastapi import APIRouter, Depends

from app.db.mongo import db
from app.modules.dashboard.schemas.dashboard import DashboardStatOut
from app.utils.auth_utils import authenticate

router = APIRouter(
    dependencies=[Depends(authenticate)]  # ✅ applies to all routes
)

products_collection = db["products"]
customers_collection = db["customers"]
orders_collection = db["orders"]

@router.get("/stats", response_model=List[DashboardStatOut])
async def get_dashboard_stats():

    total_products = await products_collection.count_documents({
        "isDeleted": False
    })

    total_draft_products = await products_collection.count_documents({
        "isDeleted": False,
        "status": "draft"
    })

    total_customers = await customers_collection.count_documents({
        "isDeleted": False
    })

    total_orders = await orders_collection.count_documents({
        "isDeleted": False
    })

    return [
        {
            "icon": "bi-box-seam",
            "value": total_products,
            "label": "Total Products",
        },
        {
            "icon": "bi-cart-dash",
            "value": total_draft_products,
            "label": "Total Draft Products",
        },
        {
            "icon": "bi-people",
            "value": total_customers,
            "label": "Total Customers",
        },
        {
            "icon": "bi-cart",
            "value": total_orders,
            "label": "Total Orders",
        },
    ]