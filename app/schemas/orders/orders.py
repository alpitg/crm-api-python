from pydantic import BaseModel, model_validator
from typing import Any, Optional, List
from datetime import datetime

from app.schemas.orders.invoice import InvoiceIn
from core.sanitize import sanitize_input

# ---------- Misc Charges ----------
class MiscCharge(BaseModel):
    label: str
    amount: float = 0.0

# ---------- Customization ----------
class FrameDetails(BaseModel):
    type: Optional[str] = 0.0
    color: Optional[str] = None
    width: Optional[float] = 0.0
    height: Optional[float] = 0.0

class GlassDetails(BaseModel):
    isEnabled: bool = False
    type: Optional[str] = None
    width: Optional[float] = 0.0
    height: Optional[float] = 0.0

class MountingDetails(BaseModel):
    isEnabled: bool = False
    top: Optional[float] = None
    right: Optional[float] = None
    bottom: Optional[float] = None
    left: Optional[float] = None

class AdditionalServices(BaseModel):
    varnish: bool
    lamination: bool
    routerCut: bool

class CustomizedDetails(BaseModel):
    name: str
    description: Optional[str]
    width: Optional[float] = 0.00
    height: Optional[float] = 0.00
    frame: Optional[FrameDetails] = None
    glass: Optional[GlassDetails] = None
    mounting: Optional[MountingDetails] = None
    additional: Optional[AdditionalServices] = None

# ---------- Order Item ----------
class OrderItemIn(BaseModel):
    productId: Optional[str] = None
    quantity: int = 0
    unitPrice: float = 0.0
    discountedQuantity: int = 0
    discountAmount: float = 0.0
    cancelledQty: Optional[int] = 0
    customizedDetails: Optional[CustomizedDetails] = None

# ---------- Main Order ----------
class OrderIn(BaseModel):
    customerName: str
    customerId: Optional[str] = None  # Use ObjectId in backend
    items: List[OrderItemIn]
    advancePayment: float = 0
    miscCharges: List[MiscCharge] = []
    paymentMode: Optional[str] = None
    paymentStatus: Optional[str] = None
    invoiceId: Optional[str] = None  # Instead of embedding invoice
    handledBy: Optional[str] = None
    createdAt: Optional[datetime] = None  # auto-fill in backend
    likelyDateOfDelivery: Optional[datetime] = None
    note: Optional[str] = ""

# ---------- Output ----------
class OrderDetailOut(OrderIn):
    id: str
    subtotal: Optional[float] = 0.0
    totalDiscountAmount: Optional[float] = 0.0
    totalAmount: Optional[float] = 0.0
    cancelledAmount: Optional[float] = 0.0

class OrderOut(BaseModel):
    id: str
    subtotal: Optional[float] = 0.0
    totalDiscountAmount: Optional[float] = 0.0
    totalAmount: Optional[float] = 0.0
    cancelledAmount: Optional[float] = 0.0

class OrderWithInvoiceIn(BaseModel):
    order: OrderIn
    invoice: Optional[InvoiceIn] = None

    @model_validator(mode="before")
    def sanitize_empty_strings(cls, values):
        return sanitize_input(values)

class OrderWithInvoiceOut(BaseModel):
    order: OrderOut
    invoice: Optional[Any] = None

    