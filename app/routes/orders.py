from typing import List
from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from datetime import datetime, timezone
from app.db.mongo import db
from app.schemas.orders.orders import OrderDetailOut, OrderIn, OrderOut, OrderWithInvoiceIn, OrderWithInvoiceOut
from app.schemas.orders.order_summary import OrderSummaryOut
from app.utils.order_util import generate_order_id
from core.sanitize import stringify_object_ids

router = APIRouter()
orders_collection = db["orders"]
customers_collection = db["customers"]
invoices_collection = db["invoices"]

@router.get("/", response_model=List[OrderSummaryOut])
async def get_all_orders():
    orders_summary = []

    async for order in orders_collection.find({}).sort("createdAt", -1):
        customer = await customers_collection.find_one({"_id": ObjectId(order["customerId"])})
        if not customer:
            customer = {"name": order.get("customerName", "")}

        # Get payment status from invoice (if available)
        invoice = await invoices_collection.find({"orderIds": order["_id"]}).sort("createdAt", -1).to_list(length=1)

        # Get the first (most recent) invoice
        invoice = invoice[0] if invoice else None

        payment_status = invoice.get("paymentStatus", "pending") if invoice else "pending"

        summary = {
            "id": str(order["_id"]),
            "orderCode": order.get("orderCode", ""),
            "customerName": customer.get("name", ""),
            "createdAt": order.get("createdAt"),
            "itemCount": len(order.get("items", [])),
            "paymentStatus": payment_status,
            "total": order.get("totalAmount", 0.0),
            "orderStatus": order.get("orderStatus", "pending"),
        }

        orders_summary.append(summary)

    return orders_summary

@router.get("/{order_id}", response_model=OrderDetailOut)
async def get_order_details(order_id: str):
    # 1. Validate order_id format
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    # 2. Fetch order
    order_doc = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order_doc:
        raise HTTPException(status_code=404, detail="Order not found")

    order_doc["id"] = order_doc.pop("_id")
    order_doc = stringify_object_ids(order_doc)

    # 3. Prepare OrderIn model (full details)
    order_in = OrderIn(**order_doc) 

    # 4. Fetch invoice if exists
    invoice_out = None
    if order_doc.get("invoiceId") and ObjectId.is_valid(order_doc["invoiceId"]):
        invoice_doc = await db.invoices.find_one({"_id": ObjectId(order_doc["invoiceId"])})
        if invoice_doc:
            invoice_out = stringify_object_ids(invoice_doc)
            invoice_out["id"] = invoice_out.pop("_id")

    # 5. Return combined response
    return OrderDetailOut(order=order_in, invoice=invoice_out)

@router.post("/place-order", response_model=OrderWithInvoiceOut, status_code=status.HTTP_201_CREATED)
async def place_order(payload: OrderWithInvoiceIn):
    '''
        | Field                 | Belongs To | Why                                            |
        | --------------------- | ---------- | ---------------------------------------------- |
        | **discount**        | `Order`    | Pricing logic at time of order placement       |
        | **advancePaid**     | `Invoice`  | Payment transaction info, affects balance owed |
        | **paymentStatus**   | `Invoice`  |                                                |
        | **paymentMode**     | `Invoice`  |                                                |
        | **orderStatus**     | `Order`    |                                                |
        | **invoiceStatus**   | `Invoice`  |                                                |

    '''

    order = payload.order
    invoice_data = payload.invoice

    order.orderCode = generate_order_id()
    order.customerId = ObjectId(order.customerId) if order.customerId and ObjectId.is_valid(order.customerId) else None

    # --- Step 1: Calculate order financials ---
    subtotal = 0.0
    total_discount = order.discountAmount
    cancelled_amount = 0.0

    #region Calculate discount per item
    for item in order.items:
        line_total = item.unitPrice * item.quantity
        subtotal += line_total

        if item.discountAmount:
            total_discount += item.discountAmount
        if item.discountedQuantity:
            total_discount += item.unitPrice * item.discountedQuantity
        if item.cancelledQty:
            cancelled_amount += item.unitPrice * item.cancelledQty
    #endregion

    # calculate misc charges & discounts
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
    if invoice_data and invoice_data.generateInvoice is True:
        # Case 1: Create a new invoice
        invoice_doc = invoice_data.model_dump()
        invoice_doc.update({
            "orderIds": [order_id],
            "totalAmount": total_amount,
            "advancePaid": invoice_data.advancePaid,
            "balanceAmount": total_amount - invoice_data.advancePaid,
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


    order_doc["id" ] = str(order_id)
    order_doc = stringify_object_ids(order_doc)

    # --- Step 5: Clean and prepare response ---
    response = {
        "order": OrderOut(**order_doc),
        "invoice": stringify_object_ids(created_invoice)
    }

    return response


