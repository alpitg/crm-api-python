from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from datetime import datetime, timezone
from app.db.mongo import db
from app.schemas.orders.orders import OrderIn, OrderOut
from app.schemas.orders.order_summary import OrderSummaryOut

#  swagger example for OrderIn
# {
#   "customerId": "68938f6b5acb0a440837ac80",
#   "status": "pending",
#   "items": [
#     {
#       "productId": "55938f6b5acb0a440837ac80",
#       "description": "string",
#       "quantity": 0,
#       "unitPrice": 0,
#       "discountedQuantity": 0,
#       "discountAmount": 0,
#       "discountPercentage": 0,
#       "cancelledQty": 0
#     }
#   ],
#   "note": ""
# }

router = APIRouter()
orders_collection = db["orders"]
customers_collection = db["customers"]
invoices_collection = db["invoices"]

@router.post("/", response_model=OrderOut)
async def place_order(payload: OrderIn):
    # Build calculated fields
    calculated_items = []
    subtotal = 0
    total_discount = 0
    cancelled_amount = 0

    for item in payload.items:
        net_qty = item.quantity - (item.cancelledQty or 0)
        amt_before_discount = net_qty * item.unitPrice
        amt_after_discount = amt_before_discount - item.discountAmount

        subtotal += amt_before_discount
        total_discount += item.discountAmount
        cancelled_amount += (item.cancelledQty or 0) * item.unitPrice

        calculated_items.append({
            "productId": ObjectId(item.productId),
            "description": item.description,
            "quantity": item.quantity,
            "unitPrice": item.unitPrice,
            "discountedQuantity": item.discountedQuantity or 0,
            "discountAmount": item.discountAmount,
            "discountPercentage": item.discountPercentage,
            "cancelledQty": item.cancelledQty or 0,
            "netQuantity": net_qty,
            "amountBeforeDiscount": amt_before_discount,
            "amountAfterDiscount": amt_after_discount
        })

    order_doc = {
        "customerId": ObjectId(payload.customerId),
        "status": payload.status,
        "items": calculated_items,
        "createdAt": datetime.now(timezone.utc),
        "subtotal": subtotal,
        "totalDiscountAmount": total_discount,
        "totalAmount": subtotal - total_discount,
        "cancelledAmount": cancelled_amount,
        "note": payload.note
    }

    result = await orders_collection.insert_one(order_doc)

    order_doc["id"] = str(result.inserted_id)
    order_doc["customerId"] = str(order_doc["customerId"])

    # Convert productId in items
    for item in order_doc["items"]:
        item["productId"] = str(item["productId"])

    order_doc.pop("_id", None)
    return order_doc



@router.get("/", response_model=List[OrderSummaryOut])
async def get_all_orders():
    orders_summary = []

    async for order in orders_collection.find({}):
        customer = await customers_collection.find_one({"_id": order["customerId"]})
        if not customer:
            continue

        # Get payment status from invoice (if available)
        invoice = await invoices_collection.find_one({"orderIds": order["_id"]})
        payment_status = invoice["paymentStatus"] if invoice and "paymentStatus" in invoice else "pending"

        summary = {
            "orderId": str(order["_id"]),
            "customerName": customer.get("name", ""),
            "date": order.get("createdAt"),
            "itemCount": len(order.get("items", [])),
            "paymentStatus": payment_status,
            "total": order.get("totalAmount", 0.0),
            "orderStatus": order.get("status", "pending"),
        }

        orders_summary.append(summary)

    return orders_summary
