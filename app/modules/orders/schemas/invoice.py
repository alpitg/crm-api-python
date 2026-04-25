from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from datetime import datetime

# Invoice Item (snapshot from order items)
class InvoiceItem(BaseModel):
    productId: Optional[str] = None
    productType: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    quantity: int = 0
    unitPrice: float = 0.0
    discountedQuantity: int = 0
    discountAmount: float = 0.0
    cancelledQty: int = 0
    taxSnapshot: List[Dict[str, Any]] = []  # copy tax details
    customizedDetails: Optional[Dict[str, Any]] = None
    lineTotal: float = 0.0  # calculated

# Party Details
class PartyDetails(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    detail: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None  # or other tax id

    @model_validator(mode="before")
    def normalize_detail(cls, values):
        if not values.get("address") and values.get("detail"):
            values["address"] = values["detail"]
        return values

# Invoice Input
class InvoiceIn(BaseModel):
    # orderIds: List[str] = Field(..., min_items=1)  # orders to invoice
    orderIds: Optional[List[str]] = None  # allow empty for manual invoice creation
    billDate: Optional[datetime] = None
    billFrom: Optional[PartyDetails] = None  # business details
    billTo: Optional[PartyDetails] = None  # customer details
    paymentMode: Optional[str] = "cash"  # cash, online, etc.
    advancePaid: float = 0.0
    generateInvoice: bool = False
    paymentStatus: Optional[str] = None

# Invoice Output
class InvoiceOut(BaseModel):
    id: Optional[str] = None
    invoiceNumber: Optional[str] = None
    # billDate: datetime
    billFrom: Optional[PartyDetails] = None
    billTo: Optional[PartyDetails] = None
    orderIds: Optional[List[str]] = None
    items: Optional[List[InvoiceItem]] = None
    subtotal: float = 0.0
    discountAmount: float = 0.0
    taxAmount: float = 0.0
    totalAmount: float = 0.0
    advancePaid: float = 0.0
    balanceAmount: float = 0.0
    paymentMode: str 
    paymentStatus: str  # pending, partial, paid
    # createdAt: datetime
    # updatedAt: datetime

# For creating invoice
class CreateInvoiceRequest(BaseModel):
    orderIds: List[str] = Field(..., min_items=1)

# For updating payment
class UpdatePaymentRequest(BaseModel):
    advancePaid: Optional[float] = None
    paymentMode: Optional[str] = None
    paymentStatus: Optional[str] = None

# For listing invoices
class InvoiceListFilters(BaseModel):
    customerId: Optional[str] = None
    paymentStatus: Optional[str] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    limit: int = 10
    offset: int = 0

# For listing invoices response with pagination
class InvoiceListResponse(BaseModel):
    invoices: List[InvoiceOut]
    total: int
    page: int
    limit: int
    pages: int
