from pydantic import BaseModel, model_validator
from typing import Any, Optional, List
from datetime import datetime

from app.modules.master.tax_rules.schemas.tax_rules import TaxRuleOut
from app.modules.orders.schemas.invoice import InvoiceIn
from core.sanitize import sanitize_input

# ---------- Misc Charges ----------
class MiscCharge(BaseModel):
    label: str
    amount: float = 0.0


# ---------- Customization ----------
class FrameDetails(BaseModel):
    type: Optional[str] = None
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
    varnish: bool = False
    lamination: bool = False
    routerCut: bool = False


class CustomizedDetails(BaseModel):
    name: str
    description: Optional[str] = None
    width: Optional[float] = 0.0
    height: Optional[float] = 0.0
    frame: Optional[FrameDetails] = None
    glass: Optional[GlassDetails] = None
    mounting: Optional[MountingDetails] = None
    additional: Optional[AdditionalServices] = None

# ---------- Order Item ----------
class OrderItemIn(BaseModel):
    productId: Optional[str] = None
    productType: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    quantity: int = 0
    unitPrice: float = 0.0
    discountedQuantity: int = 0
    discountAmount: float = 0.0
    cancelledQty: int = 0

    taxSnapshot: List[TaxRuleOut] = [] # copy tax details here at time of order

    customizedDetails: Optional[CustomizedDetails] = None

# ---------- Main Order ----------
class OrderIn(BaseModel):
    id: Optional[str] = None
    orderCode: Optional[str] = None
    customerName: str
    customerId: Optional[str] = None  # Use ObjectId in backend
    items: List[OrderItemIn]
    discountAmount: float = 0.0
    miscCharges: List[MiscCharge] = []
    orderStatus: Optional[str] = None
    invoiceId: Optional[str] = None  # Instead of embedding invoice
    handledBy: Optional[str] = None
    createdAt: Optional[datetime] = None  # auto-fill in backend
    likelyDateOfDelivery: Optional[datetime] = None
    note: Optional[str] = ""

# ---------- Output ----------
class OrderOut(OrderIn):
    subtotal: Optional[float] = 0.0
    totalDiscountAmount: Optional[float] = 0.0
    totalAmount: Optional[float] = 0.0
    cancelledAmount: Optional[float] = 0.0

class OrderWithInvoiceIn(BaseModel):
    order: OrderIn
    invoice: InvoiceIn

    @model_validator(mode="before")
    def sanitize_empty_strings(cls, values):
        return sanitize_input(values)

class OrderWithInvoiceOut(BaseModel):
    order: OrderOut
    invoice: Optional[Any] = None

class OrderDetailOut(BaseModel):
    order: OrderIn
    invoice: Optional[Any] = None
