from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from datetime import datetime, timezone
import razorpay

from app.db.mongo import db
from app.modules.orders.schemas.orders import OrderIn, PublicOrderIn, VerifyWebsitePaymentIn
from app.utils.generate_unique_id_util import generate_order_code
from core.sanitize import stringify_object_ids
from config import settings

router = APIRouter()

orders_collection = db["orders"]
customers_collection = db["customers"]
invoices_collection = db["invoices"]
products_collection = db["products"]

razorpay_client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    )
)

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_public_order(payload: PublicOrderIn):
    order = payload

    # Validate customer
    customer_id = None
    if order.customerId:
        if not ObjectId.is_valid(order.customerId):
            raise HTTPException(status_code=400, detail="Invalid customer ID")
        customer_id = ObjectId(order.customerId)

    # Calculate pricing
    subtotal = 0.0
    total_discount = float(order.discountAmount or 0)
    cancelled_amount = 0.0
    total_tax = 0.0
    processed_items = []

    for item in order.items:
        if not item.productId or not ObjectId.is_valid(item.productId):
            raise HTTPException(status_code=400, detail=f"Invalid product ID: {item.productId}")

        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than zero")

        product = await products_collection.find_one({
            "_id": ObjectId(item.productId)
        })

        if not product:
            raise HTTPException(status_code=404, detail=f"Product not found: {item.productId}")

        inventory = product.get("inventory", {})
        stock = (
            inventory.get("quantityInShelf", 0)
            + inventory.get("quantityInWarehouse", 0)
        )

        if stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.get('name')}"
            )

        # Get pricing from database
        price = product.get("price", {})
        base_price = float(price.get("basePrice") or 0)
        selling_price = float(price.get("sellingPrice") or 0)

        if selling_price <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid selling price for {product.get('name')}"
            )

        # Product discount
        product_discount_per_unit = max(
            base_price - selling_price,
            0
        )

        product_discount_amount = (
            product_discount_per_unit * item.quantity
        )

        total_discount += product_discount_amount

        # Line subtotal
        line_subtotal = base_price * item.quantity
        subtotal += line_subtotal

        # Tax
        tax = price.get("tax", {})
        tax_included = bool(tax.get("included", True))
        tax_rate = float(tax.get("rate") or 0)
        tax_class_name = tax.get("className")

        line_tax = 0.0

        if tax_rate > 0 and not tax_included:
            line_tax = line_subtotal * tax_rate / 100
            total_tax += line_tax

        # Tax snapshot
        tax_snapshot = []

        if tax_class_name or tax_rate > 0:
            tax_snapshot = [{
                "className": tax_class_name,
                "rate": tax_rate,
                "included": tax_included
            }]

        # Build item snapshot
        processed_item = {
            "productId": item.productId,
            "productType": (
                item.productType
                or product.get("productType", "physical")
            ),
            "name": product.get("name"),
            "description": product.get("description"),
            "quantity": item.quantity,
            "unitPrice": selling_price,
            "discountedQuantity": (
                item.quantity
                if product_discount_amount > 0
                else 0
            ),
            "discountAmount": product_discount_amount,
            "cancelledQty": 0,
            "taxSnapshot": tax_snapshot,
            "customizedDetails": (
                item.customizedDetails.model_dump()
                if item.customizedDetails
                else {}
            )
        }

        processed_items.append(processed_item)

    # Misc charges
    misc_charges = order.miscCharges or []

    misc_total = sum(
        float(charge.amount)
        for charge in misc_charges
    )

    # Final amount
    total_amount = (
        subtotal
        - total_discount
        - cancelled_amount
        + total_tax
        + misc_total
    )

    if total_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid order amount"
        )

    order_code = generate_order_code()
    now = datetime.now(timezone.utc)

    # Create Order
    order_doc = {
        "orderCode": order_code,
        "customerName": order.customerName,
        "customerId": customer_id,
        "items": processed_items,
        "discountAmount": float(order.discountAmount or 0),
        "miscCharges": misc_charges,
        "orderStatus": "payment_pending",
        "invoiceId": None,
        "handledBy": None,
        "createdAt": now,
        "likelyDateOfDelivery": order.likelyDateOfDelivery,
        "note": order.note or "Website order",
        "subtotal": subtotal,
        "totalDiscountAmount": total_discount,
        "totalAmount": total_amount,
        "cancelledAmount": cancelled_amount
    }

    # Insert Order
    result = await orders_collection.insert_one(order_doc)

    if not result.inserted_id:
        raise HTTPException(
            status_code=500,
            detail="Failed to create order"
        )

    order_id = result.inserted_id
    invoice_id = None
    razorpay_order = None

    try:
        # Create Invoice
        invoice_doc = {
            "orderIds": [order_id],
            "billDate": None,
            "billFrom": None,
            "billTo": {
                "name": order.customerName,
                "address": None,
                "detail": None,
                "phone": None,
                "email": None,
                "gstin": None
            },
            "paymentMode": "online",
            "paymentProvider": "razorpay",
            "paymentMethod": None,
            "advancePaid": 0,
            "generateInvoice": True,
            "paymentStatus": "pending",
            "totalAmount": total_amount,
            "balanceAmount": total_amount,
            "razorpay": {
                "orderId": None,
                "paymentId": None,
                "signature": None
            },
            "createdAt": now
        }

        invoice_result = await invoices_collection.insert_one(invoice_doc)

        if not invoice_result.inserted_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to create invoice"
            )

        invoice_id = invoice_result.inserted_id

        # Create Razorpay Order
        razorpay_order = razorpay_client.order.create({
            "amount": int(round(total_amount * 100)),
            "currency": "INR",
            "receipt": order_code,
            "payment_capture": 1,
            "notes": {
                "order_id": str(order_id),
                "order_code": order_code,
                "invoice_id": str(invoice_id)
            }
        })

        if not razorpay_order.get("id"):
            raise HTTPException(
                status_code=500,
                detail="Failed to create Razorpay order"
            )

        # Update Invoice with Razorpay Order ID
        await invoices_collection.update_one(
            {"_id": invoice_id},
            {
                "$set": {
                    "razorpay.orderId": razorpay_order["id"]
                }
            }
        )

        # Update Order with Invoice ID
        await orders_collection.update_one(
            {"_id": order_id},
            {
                "$set": {
                    "invoiceId": str(invoice_id)
                }
            }
        )

    except HTTPException:
        await orders_collection.delete_one({"_id": order_id})

        if invoice_id:
            await invoices_collection.delete_one({"_id": invoice_id})

        raise

    except Exception as exc:
        await orders_collection.delete_one({"_id": order_id})

        if invoice_id:
            await invoices_collection.delete_one({"_id": invoice_id})

        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize payment: {str(exc)}"
        )

    # Get final order
    created_order = await orders_collection.find_one({
        "_id": order_id
    })

    # Get final invoice
    created_invoice = await invoices_collection.find_one({
        "_id": invoice_id
    })

    response =  {
        "order": stringify_object_ids(created_order),
        "invoice": stringify_object_ids(created_invoice),
        "payment": {
            "provider": "razorpay",
            "keyId": settings.RAZORPAY_KEY_ID,
            "razorpayOrderId": razorpay_order["id"],
            "amount": razorpay_order["amount"],
            "currency": razorpay_order["currency"]
        }
    }

    return response


@router.post("/verify-payment")
async def verify_website_payment(
    payload: VerifyWebsitePaymentIn
):
    # Validate internal order ID
    if not ObjectId.is_valid(payload.orderId):
        raise HTTPException(
            status_code=400,
            detail="Invalid order ID"
        )

    order_id = ObjectId(payload.orderId)

    # Get order from database
    order = await orders_collection.find_one({
        "_id": order_id
    })

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    # Already paid / verified
    if order.get("orderStatus") == "placed":
        return {
            "success": True,
            "message": "Payment already verified",
            "order": stringify_object_ids(order)
        }

    # Get invoice
    invoice_id = order.get("invoiceId")

    if not invoice_id:
        raise HTTPException(
            status_code=400,
            detail="Invoice not found for this order"
        )

    if not ObjectId.is_valid(invoice_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid invoice ID"
        )

    invoice = await invoices_collection.find_one({
        "_id": ObjectId(invoice_id)
    })

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )

    # Get Razorpay order ID from YOUR database
    razorpay_order_id = (
        invoice.get("razorpay", {})
        .get("orderId")
    )

    if not razorpay_order_id:
        raise HTTPException(
            status_code=400,
            detail="Razorpay order ID not found"
        )

    # Never trust the Razorpay order ID from frontend
    if razorpay_order_id != payload.razorpayOrderId:
        raise HTTPException(
            status_code=400,
            detail="Razorpay order mismatch"
        )

    # Prevent payment ID reuse
    existing_payment_id = (
        invoice.get("razorpay", {})
        .get("paymentId")
    )

    if existing_payment_id:
        if existing_payment_id == payload.razorpayPaymentId:
            return {
                "success": True,
                "message": "Payment already verified",
                "order": stringify_object_ids(order),
                "invoice": stringify_object_ids(invoice)
            }

        raise HTTPException(
            status_code=400,
            detail="Invoice already has a payment"
        )

    # Verify Razorpay signature
    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id":
                razorpay_order_id,
            "razorpay_payment_id":
                payload.razorpayPaymentId,
            "razorpay_signature":
                payload.razorpaySignature
        })

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment signature"
        )

    # Fetch payment from Razorpay
    try:
        payment = razorpay_client.payment.fetch(
            payload.razorpayPaymentId
        )

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Unable to fetch payment details"
        )

    # Verify payment belongs to the same Razorpay order
    if payment.get("order_id") != razorpay_order_id:
        raise HTTPException(
            status_code=400,
            detail="Payment does not belong to this order"
        )

    # Verify payment amount
    expected_amount = int(
        round(
            float(order.get("totalAmount", 0))
            * 100
        )
    )

    actual_amount = int(
        payment.get("amount", 0)
    )

    if actual_amount != expected_amount:
        raise HTTPException(
            status_code=400,
            detail="Payment amount mismatch"
        )

    # Verify currency
    if payment.get("currency") != "INR":
        raise HTTPException(
            status_code=400,
            detail="Invalid payment currency"
        )

    # Verify captured status
    payment_status = payment.get("status")

    if payment_status != "captured":
        raise HTTPException(
            status_code=400,
            detail=f"Payment is not captured. Current status: {payment_status}"
        )

    now = datetime.now(timezone.utc)

    # Payment method
    payment_method = payment.get("method")

    # Update Invoice
    invoice_update = {
        "paymentStatus": "paid",
        "paymentMode": "online",
        "paymentProvider": "razorpay",
        "paymentMethod": payment_method,
        "advancePaid": float(
            order.get("totalAmount", 0)
        ),
        "balanceAmount": 0,
        "razorpay.paymentId":
            payload.razorpayPaymentId,
        "razorpay.orderId":
            razorpay_order_id,
        "razorpay.signature":
            payload.razorpaySignature,
        "paidAt": now,
        "updatedAt": now
    }

    await invoices_collection.update_one(
        {
            "_id": ObjectId(invoice_id)
        },
        {
            "$set": invoice_update
        }
    )

    # Update Order
    await orders_collection.update_one(
        {
            "_id": order_id
        },
        {
            "$set": {
                "orderStatus": "placed",
                "updatedAt": now
            }
        }
    )

    # Get updated order
    updated_order = await orders_collection.find_one({
        "_id": order_id
    })

    # Get updated invoice
    updated_invoice = await invoices_collection.find_one({
        "_id": ObjectId(invoice_id)
    })

    return {
        "success": True,
        "message": "Payment verified successfully",
        "order": stringify_object_ids(
            updated_order
        ),
        "invoice": stringify_object_ids(
            updated_invoice
        ),
        "payment": {
            "provider": "razorpay",
            "paymentId":
                payload.razorpayPaymentId,
            "razorpayOrderId":
                razorpay_order_id,
            "paymentMethod":
                payment_method,
            "amount":
                payment.get("amount"),
            "currency":
                payment.get("currency"),
            "status":
                payment_status,
            "paidAt":
                now
        }
    }