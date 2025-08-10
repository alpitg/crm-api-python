from typing import List
from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from datetime import datetime, timezone
from app.db.mongo import db
from app.schemas.orders.orders import OrderDetailOut, OrderOut, OrderWithInvoiceIn, OrderWithInvoiceOut
from app.schemas.orders.order_summary import OrderSummaryOut
from core.sanitize import stringify_object_ids

router = APIRouter()
orders_collection = db["orders"]
customers_collection = db["customers"]
invoices_collection = db["invoices"]

@router.get("/", response_model=List[OrderSummaryOut])
async def get_all_orders():
    orders_summary = []

    async for order in orders_collection.find({}):
        customer = await customers_collection.find_one({"_id": ObjectId(order["customerId"])})
        if not customer:
            customer = {"name": order.get("customerName", "")}

        # Get payment status from invoice (if available)
        invoice = await invoices_collection.find_one({"orderIds": order["_id"]})
        payment_status = invoice["paymentStatus"] if invoice and "paymentStatus" in invoice else "pending"

        summary = {
            "orderId": str(order["_id"]),
            "customerName": customer.get("name", ""),
            "createdAt": order.get("createdAt"),
            "itemCount": len(order.get("items", [])),
            "paymentStatus": payment_status,
            "total": order.get("totalAmount", 0.0),
            "orderStatus": order.get("status", "pending"),
        }

        orders_summary.append(summary)

    return orders_summary

@router.get("/{order_id}", response_model=OrderDetailOut)
async def get_order_details(order_id: str):
    # Validate ObjectId format
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    # Fetch order from DB
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order = stringify_object_ids(order)
    order["id"] = order.pop("_id")

    # Return as OrderOut
    return OrderDetailOut(**order)


@router.post("/place-order", response_model=OrderWithInvoiceOut, status_code=status.HTTP_201_CREATED)
async def place_order(payload: OrderWithInvoiceIn):

    order = payload.order
    invoice_data = payload.invoice
    order.customerId = ObjectId(order.customerId) if order.customerId and ObjectId.is_valid(order.customerId) else None

    # --- Step 1: Calculate order financials ---
    subtotal = 0.0
    total_discount = 0.0
    cancelled_amount = 0.0

    for item in order.items:
        line_total = item.unitPrice * item.quantity
        subtotal += line_total

        if item.discountAmount:
            total_discount += item.discountAmount
        if item.discountedQuantity:
            total_discount += item.unitPrice * item.discountedQuantity
        if item.cancelledQty:
            cancelled_amount += item.unitPrice * item.cancelledQty

    misc_total = sum(charge.amount for charge in order.miscCharges)
    total_amount = (subtotal - total_discount - cancelled_amount) + misc_total

    # --- Step 2: Prepare order document ---
    now = datetime.now(timezone.utc)
    order_doc = order.model_dump()
    order_doc.update({
        "subtotal": subtotal,
        "totalDiscountAmount": total_discount,
        "totalAmount": total_amount,
        "cancelledAmount": cancelled_amount,
        "createdAt": order.createdAt or now,
    })

    # --- Step 3: Insert order ---
    result = await orders_collection.insert_one(order_doc)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to insert order")

    order_id = result.inserted_id
    created_invoice = None

    # --- Step 4: Handle Invoice Logic ---
    if invoice_data:
        # Case 1: Create a new invoice
        invoice_doc = invoice_data.model_dump()
        invoice_doc.update({
            "orderIds": [order_id],
            "totalAmount": total_amount,
            "advancePaid": order.advancePayment,
            "balanceAmount": total_amount - order.advancePayment,
            "createdAt": now
        })

        invoice_result = await invoices_collection.insert_one(invoice_doc)
        if not invoice_result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create invoice")

        invoice_id_str = str(invoice_result.inserted_id)
        created_invoice = {
            "_id": invoice_id_str,
            **invoice_doc
        }

        # Update the inserted order with this invoiceId
        await orders_collection.update_one(
            {"_id": order_id},
            {"$set": {"invoiceId": invoice_id_str}}
        )

        # Also update the order_doc for return
        order_doc["invoiceId"] = invoice_id_str

    elif order.invoiceId:
        # Case 2: Link this order to an existing invoice
        try:
            invoice_obj_id = ObjectId(order.invoiceId)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid invoiceId format")

        update_result = await invoices_collection.update_one(
            {"_id": invoice_obj_id},
            {
                "$push": {"orderIds": order_id},
                "$inc": {
                    "totalAmount": total_amount,
                    "advancePaid": order.advancePayment,
                    "balanceAmount": total_amount - order.advancePayment
                }
            }
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Update the order_doc for return
        order_doc["invoiceId"] = order.invoiceId

    # --- Step 5: Clean and prepare response ---
    response = {
        "order": OrderOut(
            id=str(order_id),
            subtotal=subtotal,
            totalDiscountAmount=total_discount,
            totalAmount=total_amount,
            cancelledAmount=cancelled_amount,
        ),
        "invoice": stringify_object_ids(created_invoice)
    }

    return response


