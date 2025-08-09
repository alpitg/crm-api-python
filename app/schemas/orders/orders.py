from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.schemas.orders.invoice import InvoiceIn

# ---------- Misc Charges ----------
class MiscCharge(BaseModel):
    label: str
    amount: float

# ---------- Customization ----------
class FrameDetails(BaseModel):
    type: str
    color: str
    width: float
    height: float

class GlassDetails(BaseModel):
    isEnabled: bool = False
    type: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None

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
    description: str
    width: float
    height: float
    frame: Optional[FrameDetails] = None
    glass: Optional[GlassDetails] = None
    mounting: Optional[MountingDetails] = None
    additional: Optional[AdditionalServices] = None

# ---------- Order Item ----------
class OrderItemIn(BaseModel):
    productId: str
    quantity: int
    unitPrice: float
    discountedQuantity: int = 0
    discountAmount: float = 0.0
    cancelledQty: Optional[int] = 0
    customizedDetails: Optional[CustomizedDetails] = None

# ---------- Main Order ----------
class OrderIn(BaseModel):
    customerId: str
    items: List[OrderItemIn]
    note: str = ""
    advancePayment: float = 0
    miscCharges: List[MiscCharge] = []
    paymentMode: Optional[str] = None
    paymentStatus: Optional[str] = None
    invoiceId: Optional[str] = None  # Instead of embedding invoice
    handledBy: Optional[str] = None
    createdAt: Optional[datetime] = None  # auto-fill in backend
    likelyDateOfDelivery: Optional[datetime] = None

class OrderWithInvoiceIn(BaseModel):
    order: OrderIn
    invoice: Optional[InvoiceIn] = None

# ---------- Output ----------
class OrderOut(BaseModel):
    id: str
    subtotal: Optional[float] = 0.0
    totalDiscountAmount: Optional[float] = 0.0
    totalAmount: Optional[float] = 0.0
    cancelledAmount: Optional[float] = 0.0
