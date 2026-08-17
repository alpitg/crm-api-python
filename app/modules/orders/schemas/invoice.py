from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class InvoiceItem(BaseModel):
    """Invoice item snapshot."""

    productId: Optional[str] = None
    productType: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None

    quantity: int = Field(
        default=0,
        ge=0,
    )

    unitPrice: float = Field(
        default=0.0,
        ge=0,
    )

    mrp: float = Field(
        default=0.0,
        ge=0,
    )

    discountedQuantity: int = Field(
        default=0,
        ge=0,
    )

    discountAmount: float = Field(
        default=0.0,
        ge=0,
    )

    cancelledQty: int = Field(
        default=0,
        ge=0,
    )

    taxSnapshot: List[dict] = Field(
        default_factory=list
    )

    lineTotal: float = Field(
        default=0.0,
        ge=0,
    )


class PartyDetails(BaseModel):
    """Customer or business billing details."""

    name: Optional[str] = None
    address: Optional[str] = None
    detail: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_detail(cls, values):
        if not isinstance(values, dict):
            return values

        if not values.get("address") and values.get("detail"):
            values["address"] = values["detail"]

        return values


class InvoiceIn(BaseModel):
    """Invoice creation input."""

    orderIds: Optional[List[str]] = None

    billDate: Optional[datetime] = None

    billFrom: Optional[PartyDetails] = None

    billTo: Optional[PartyDetails] = None

    paymentMode: Optional[str] = "cash"

    advancePaid: float = Field(
        default=0.0,
        ge=0,
    )

    generateInvoice: bool = False

    paymentStatus: Optional[str] = None


class InvoiceOut(BaseModel):
    """Invoice response."""

    id: Optional[str] = None

    invoiceNumber: Optional[str] = None

    billDate: Optional[datetime] = None

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

    paymentMode: str = "cash"

    paymentStatus: str = "pending"

    createdAt: Optional[datetime] = None

    updatedAt: Optional[datetime] = None


class CreateInvoiceRequest(BaseModel):
    """Request for creating an invoice from orders."""

    orderIds: List[str] = Field(
        ...,
        min_length=1,
    )


class UpdatePaymentRequest(BaseModel):
    """Request for updating invoice payment."""

    advancePaid: Optional[float] = Field(
        default=None,
        ge=0,
    )

    paymentMode: Optional[str] = None

    paymentStatus: Optional[str] = None


class InvoiceListFilters(BaseModel):
    """Invoice listing filters."""

    customerId: Optional[str] = None

    paymentStatus: Optional[str] = None

    startDate: Optional[datetime] = None

    endDate: Optional[datetime] = None

    limit: int = Field(
        default=10,
        ge=1,
        le=100,
    )

    offset: int = Field(
        default=0,
        ge=0,
    )


class InvoiceListResponse(BaseModel):
    """Paginated invoice response."""

    invoices: List[InvoiceOut]

    total: int

    page: int

    limit: int

    pages: int