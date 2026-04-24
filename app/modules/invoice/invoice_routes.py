from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Optional
from bson import ObjectId

from app.modules.orders.schemas.invoice import (
    CreateInvoiceRequest, InvoiceOut, UpdatePaymentRequest, InvoiceListFilters
)
from app.modules.invoice.invoice_service import InvoiceService
from app.modules.invoice.pdf_service import PDFService
from app.utils.auth_utils import authenticate  # Assuming admin auth

router = APIRouter()

@router.post("/", response_model=InvoiceOut)
async def create_invoice(
    request: CreateInvoiceRequest,
    current_user: dict = Depends(authenticate)
):
    """Create invoice from selected orders"""
    try:
        # Build InvoiceIn from request
        from app.modules.orders.schemas.invoice import InvoiceIn, PartyDetails

        # For billFrom, get from settings or config
        # Assuming we have business details in config
        bill_from = PartyDetails(
            name="Your Business Name",
            address="Business Address",
            phone="Business Phone",
            email="business@email.com",
            gstin="GSTIN123456"
        )

        # Get billTo from orders (first order's customer)
        order_ids = [ObjectId(oid) for oid in request.orderIds]
        from app.db.mongo import db
        first_order = await db["orders"].find_one({"_id": {"$in": order_ids}})
        if not first_order:
            raise HTTPException(status_code=404, detail="Orders not found")

        customer = await db["customers"].find_one({"_id": ObjectId(first_order["customerId"])})
        bill_to = PartyDetails(
            name=customer.get("name", ""),
            address=customer.get("address", ""),
            phone=customer.get("phone", ""),
            email=customer.get("email", ""),
            gstin=customer.get("gstin")
        )

        invoice_data = InvoiceIn(
            orderIds=request.orderIds,
            billFrom=bill_from,
            billTo=bill_to
        )

        invoice = await InvoiceService.create_invoice(invoice_data)
        return invoice

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: str,
    current_user: dict = Depends(authenticate)
):
    """Get invoice by ID"""
    try:
        invoice = await InvoiceService.get_invoice_by_id(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=List[InvoiceOut])
async def list_invoices(
    customerId: Optional[str] = None,
    paymentStatus: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    current_user: dict = Depends(authenticate)
):
    """List invoices with filters"""
    try:
        filters = {}
        if customerId:
            filters["customerId"] = customerId
        if paymentStatus:
            filters["paymentStatus"] = paymentStatus

        invoices = await InvoiceService.list_invoices(filters, limit, offset)
        return invoices
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{invoice_id}/payment", response_model=InvoiceOut)
async def update_payment(
    invoice_id: str,
    request: UpdatePaymentRequest,
    current_user: dict = Depends(authenticate)
):
    """Update payment details"""
    try:
        update_data = request.dict(exclude_unset=True)
        invoice = await InvoiceService.update_payment(invoice_id, update_data)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: str,
    current_user: dict = Depends(authenticate)
):
    """Download invoice as PDF"""
    try:
        invoice = await InvoiceService.get_invoice_by_id(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        pdf_buffer = PDFService.generate_invoice_pdf(invoice)

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=invoice_{invoice.invoiceNumber}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error generating PDF")