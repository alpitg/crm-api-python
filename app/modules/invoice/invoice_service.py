from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId
from typing import List, Dict, Any, Optional
import math

from app.db.mongo import db
from app.modules.orders.schemas.invoice import InvoiceIn, InvoiceOut, InvoiceItem, PartyDetails
from app.modules.orders.schemas.orders import OrderIn, OrderItemIn
from core.sanitize import stringify_object_ids

# Collections
invoices_collection: AsyncIOMotorCollection = db["invoices"]
orders_collection: AsyncIOMotorCollection = db["orders"]
counters_collection: AsyncIOMotorCollection = db["counters"]

class InvoiceService:
    @staticmethod
    async def get_next_invoice_number() -> str:
        """Generate unique invoice number with concurrency safety"""
        today = datetime.now().strftime("%Y%m%d")

        # Use MongoDB's atomic operations for counter
        result = await counters_collection.find_one_and_update(
            {"_id": f"invoice_{today}"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True
        )

        seq = result["seq"]
        return f"INV-{today}-{seq:04d}"

    @staticmethod
    def calculate_item_total(item: OrderItemIn) -> float:
        """Calculate total for an order item"""
        billable_qty = item.quantity - item.cancelledQty
        if billable_qty <= 0:
            return 0.0

        # Apply discount
        discounted_qty = min(item.discountedQuantity, billable_qty)
        regular_qty = billable_qty - discounted_qty

        regular_total = regular_qty * item.unitPrice
        discounted_total = discounted_qty * (item.unitPrice - item.discountAmount)

        return round(regular_total + discounted_total, 2)

    @staticmethod
    def calculate_tax_amount(item_total: float, tax_rules: List[Dict[str, Any]]) -> float:
        """Calculate tax amount for an item"""
        tax_amount = 0.0
        for tax in tax_rules:
            if tax.get("isEnabled", False):
                rate = tax.get("rate", 0.0)
                tax_amount += item_total * (rate / 100)
        return round(tax_amount, 2)

    @staticmethod
    async def create_invoice(invoice_data: InvoiceIn) -> InvoiceOut:
        """Create invoice from orders"""
        # Validate orders exist and not already invoiced
        order_ids = [ObjectId(oid) for oid in invoice_data.orderIds]
        orders = await orders_collection.find({"_id": {"$in": order_ids}}).to_list(None)

        if len(orders) != len(invoice_data.orderIds):
            raise ValueError("Some orders not found")

        # Check if any order already has invoice
        invoiced_orders = [o for o in orders if o.get("invoiceId")]
        if invoiced_orders:
            raise ValueError("Some orders are already invoiced")

        # Get customer details from first order (assuming same customer)
        first_order = orders[0]
        customer_id = first_order.get("customerId")

        # For billTo, fetch customer details if available, otherwise fall back to order fields
        customer = None
        if customer_id and ObjectId.is_valid(str(customer_id)):
            customer = await db["customers"].find_one({"_id": ObjectId(customer_id)})

        if customer:
            bill_to = PartyDetails(
                name=customer.get("name", ""),
                address=customer.get("address", ""),
                phone=customer.get("phone", ""),
                email=customer.get("email", ""),
                gstin=customer.get("gstin")
            )
        else:
            bill_to = PartyDetails(
                name=first_order.get("customerName") or "Unknown Customer",
                address=first_order.get("customerAddress", "") if isinstance(first_order.get("customerAddress"), str) else "",
                phone=first_order.get("customerPhone", "") if isinstance(first_order.get("customerPhone"), str) else "",
                email=first_order.get("customerEmail", "") if isinstance(first_order.get("customerEmail"), str) else "",
                gstin=""
            )

        # Aggregate items from all orders
        all_items: List[InvoiceItem] = []
        subtotal = 0.0
        total_discount = 0.0
        total_tax = 0.0

        for order in orders:
            order_discount = order.get("discountAmount", 0.0)
            # Distribute order discount proportionally
            order_items = order.get("items", [])
            order_subtotal = sum(InvoiceService.calculate_item_total(OrderItemIn(**item)) for item in order_items)
            order_taxable = order_subtotal - order_discount

            for item_data in order_items:
                item = OrderItemIn(**item_data)
                item_total = InvoiceService.calculate_item_total(item)
                if item_total <= 0:
                    continue

                # Proportional discount
                item_discount = (item_total / order_subtotal) * order_discount if order_subtotal > 0 else 0.0
                item_taxable = item_total - item_discount

                # Tax
                tax_amount = InvoiceService.calculate_tax_amount(item_taxable, item.taxSnapshot)

                invoice_item = InvoiceItem(
                    **item_data,
                    lineTotal=round(item_taxable + tax_amount, 2)
                )
                all_items.append(invoice_item)

                subtotal += item_total
                total_discount += item_discount
                total_tax += tax_amount

        # Misc charges from orders (if any)
        misc_charges = []
        for order in orders:
            misc_charges.extend(order.get("miscCharges", []))

        misc_total = sum(charge.get("amount", 0.0) for charge in misc_charges)
        subtotal += misc_total

        total_amount = round(subtotal - total_discount + total_tax, 2)
        balance_amount = round(total_amount - invoice_data.advancePaid, 2)

        # Generate invoice number
        invoice_number = await InvoiceService.get_next_invoice_number()

        # Create invoice document
        invoice_doc = {
            "invoiceNumber": invoice_number,
            "billDate": invoice_data.billDate or datetime.now(),
            "billFrom": invoice_data.billFrom.dict(),
            "billTo": bill_to.dict(),
            "orderIds": invoice_data.orderIds,
            "items": [item.dict() for item in all_items],
            "subtotal": subtotal,
            "discountAmount": total_discount,
            "taxAmount": total_tax,
            "totalAmount": total_amount,
            "advancePaid": invoice_data.advancePaid,
            "balanceAmount": balance_amount,
            "paymentMode": invoice_data.paymentMode,
            "paymentStatus": "pending" if balance_amount > 0 else "paid",
            "createdAt": datetime.now(),
            "updatedAt": datetime.now()
        }

        # Insert invoice
        result = await invoices_collection.insert_one(invoice_doc)
        invoice_doc["id"] = str(result.inserted_id)
        invoice_doc.pop("_id", None)

        # Update orders with invoiceId
        await orders_collection.update_many(
            {"_id": {"$in": order_ids}},
            {"$set": {"invoiceId": str(result.inserted_id)}}
        )

        return InvoiceOut(**invoice_doc)

    @staticmethod
    async def get_invoice_by_id(invoice_id: str) -> Optional[InvoiceOut]:
        """Get invoice by ID"""
        invoice = await invoices_collection.find_one({"_id": ObjectId(invoice_id)})
        if invoice:
            invoice = stringify_object_ids(invoice)
            return InvoiceOut(**invoice)
        return None

    @staticmethod
    async def list_invoices(filters: Dict[str, Any], limit: int = 10, offset: int = 0) -> tuple[List[InvoiceOut], int]:
        """List invoices with filters and return total count"""
        query = {}

        # Search by invoice number
        if filters.get("search"):
            query["invoiceNumber"] = {"$regex": filters["search"], "$options": "i"}

        if filters.get("customerId"):
            # Find orders by customer, then invoices
            order_ids = await orders_collection.distinct("_id", {"customerId": ObjectId(filters["customerId"])})
            query["orderIds"] = {"$in": [str(oid) for oid in order_ids]}

        if filters.get("paymentStatus"):
            query["paymentStatus"] = filters["paymentStatus"]

        if filters.get("startDate") or filters.get("endDate"):
            date_query = {}
            if filters.get("startDate"):
                date_query["$gte"] = filters["startDate"]
            if filters.get("endDate"):
                date_query["$lte"] = filters["endDate"]
            query["billDate"] = date_query

        # Get total count
        total = await invoices_collection.count_documents(query)

        # Get invoices
        invoices = await invoices_collection.find(query).skip(offset).limit(limit).sort("createdAt", -1).to_list(None)
        return [InvoiceOut(**stringify_object_ids(inv)) for inv in invoices], total

    @staticmethod
    async def update_payment(invoice_id: str, update_data: Dict[str, Any]) -> Optional[InvoiceOut]:
        """Update payment details"""
        update_fields = {"updatedAt": datetime.now()}

        if "advancePaid" in update_data:
            update_fields["advancePaid"] = update_data["advancePaid"]
            # Recalculate balance
            invoice = await invoices_collection.find_one({"_id": ObjectId(invoice_id)})
            if invoice:
                new_balance = round(invoice["totalAmount"] - update_data["advancePaid"], 2)
                update_fields["balanceAmount"] = new_balance
                if new_balance <= 0:
                    update_fields["paymentStatus"] = "paid"
                elif update_data["advancePaid"] > 0:
                    update_fields["paymentStatus"] = "partial"

        if "paymentMode" in update_data:
            update_fields["paymentMode"] = update_data["paymentMode"]

        if "paymentStatus" in update_data:
            update_fields["paymentStatus"] = update_data["paymentStatus"]

        result = await invoices_collection.find_one_and_update(
            {"_id": ObjectId(invoice_id)},
            {"$set": update_fields},
            return_document=True
        )

        if result:
            return InvoiceOut(**stringify_object_ids(result))
        return None