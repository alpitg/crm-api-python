from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.modules.orders.schemas.invoice import InvoiceIn
from core.sanitize import sanitize_input


class MiscCharge(BaseModel):
    label: str = Field(..., min_length=1)
    amount: float = Field(default=0.0, ge=0)


class OrderItemIn(BaseModel):
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

    taxSnapshot: list[dict[str, Any]] = Field(
        default_factory=list
    )


class PublicDeliveryAddressIn(BaseModel):
    """Delivery address snapshot stored against the order."""

    name: str = Field(
        ...,
        min_length=1,
    )

    mobile: str = Field(
        ...,
        min_length=1,
    )

    addressType: str = Field(
        default="home",
        min_length=1,
    )

    addressLine1: str = Field(
        ...,
        min_length=1,
    )

    addressLine2: Optional[str] = None
    landmark: Optional[str] = None

    city: str = Field(
        ...,
        min_length=1,
    )

    state: str = Field(
        ...,
        min_length=1,
    )

    pincode: str = Field(
        ...,
        min_length=1,
    )


class PublicOrderItemIn(BaseModel):
    """
    Checkout item sent by the website.

    The frontend sends only the product ID,
    product type and quantity.

    Pricing is calculated by the backend.
    """

    productId: str = Field(
        ...,
        min_length=1,
    )

    productType: str = Field(
        default="physical",
        min_length=1,
    )

    quantity: int = Field(
        ...,
        gt=0,
    )


class PublicOrderIn(BaseModel):
    """
    Public website checkout payload.

    Pricing values are calculated by the backend.
    """

    customerName: str = Field(
        ...,
        min_length=1,
    )

    # Authenticated customer ID.
    customerId: Optional[str] = None

    # Guest cart identity.
    #
    # IMPORTANT:
    # Do not put guestCartId inside customerId.
    #
    # For authenticated checkout:
    #   customerId = customer ObjectId
    #   guestCartId = None
    #
    # For guest checkout:
    #   customerId = None
    #   guestCartId = guest cart UUID
    guestCartId: Optional[str] = None

    deliveryAddress: PublicDeliveryAddressIn

    paymentMethod: Literal[
        "cod",
        "online",
    ] = "online"

    items: list[PublicOrderItemIn] = Field(
        ...,
        min_length=1,
    )

    miscCharges: list[MiscCharge] = Field(
        default_factory=list
    )

    note: Optional[str] = "Website order"

    discountAmount: float = Field(
        default=0.0,
        ge=0,
    )

    likelyDateOfDelivery: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def sanitize_payload(cls, values: Any) -> Any:
        return sanitize_input(values)


class PublicOrderWithPaymentIn(BaseModel):
    order: PublicOrderIn


class VerifyWebsitePaymentIn(BaseModel):
    orderId: str = Field(
        ...,
        min_length=1,
    )

    razorpayPaymentId: str = Field(
        ...,
        min_length=1,
    )

    razorpayOrderId: str = Field(
        ...,
        min_length=1,
    )

    razorpaySignature: str = Field(
        ...,
        min_length=1,
    )


class OrderIn(BaseModel):
    id: Optional[str] = None
    orderCode: Optional[str] = None

    customerName: str = Field(
        ...,
        min_length=1,
    )

    customerId: Optional[str] = None

    # Keep guestCartId on the order as well so that
    # payment completion can clear the correct guest cart.
    guestCartId: Optional[str] = None

    items: list[OrderItemIn] = Field(
        default_factory=list
    )

    deliveryAddress: Optional[
        PublicDeliveryAddressIn
    ] = None

    paymentMethod: Optional[
        Literal["cod", "online"]
    ] = None

    paymentStatus: Optional[str] = None

    discountAmount: float = Field(
        default=0.0,
        ge=0,
    )

    miscCharges: list[MiscCharge] = Field(
        default_factory=list
    )

    shippingAmount: float = Field(
        default=0.0,
        ge=0,
    )

    orderStatus: Optional[str] = None

    invoiceId: Optional[str] = None

    handledBy: Optional[str] = None

    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    likelyDateOfDelivery: Optional[datetime] = None

    note: Optional[str] = ""


class OrderOut(OrderIn):
    subtotal: float = 0.0

    totalDiscountAmount: float = 0.0

    totalTaxAmount: float = 0.0

    includedTaxAmount: float = 0.0

    excludedTaxAmount: float = 0.0

    totalAmount: float = 0.0

    cancelledAmount: float = 0.0


class OrderWithInvoiceIn(BaseModel):
    order: OrderIn
    invoice: Optional[InvoiceIn] = None

    @model_validator(mode="before")
    @classmethod
    def sanitize_empty_strings(
        cls,
        values: Any,
    ) -> Any:
        return sanitize_input(values)


class OrderWithInvoiceOut(BaseModel):
    order: OrderOut
    invoice: Optional[Any] = None


class OrderDetailOut(BaseModel):
    order: OrderOut
    invoice: Optional[Any] = None


class OrderSummaryOut(BaseModel):
    id: str
    orderCode: str
    customerName: str
    createdAt: Optional[datetime] = None
    itemCount: int
    paymentStatus: Optional[str] = None
    total: float
    orderStatus: Optional[str] = None

    class Config:
        populate_by_name = True


class PaginatedOrdersOut(BaseModel):
    total: int
    page: int
    pageSize: int
    pages: int
    items: list[OrderSummaryOut]


class GetOrdersFilterIn(BaseModel):
    customerName: Optional[str] = Field(
        default=None,
        description=(
            "Filter orders by customer name "
            "(partial match)"
        ),
    )

    orderCode: Optional[str] = Field(
        default=None,
        description=(
            "Filter orders by order code "
            "(exact or partial match)"
        ),
    )

    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-based)",
    )

    pageSize: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of results per page",
    )

    sort: Optional[
        Literal["newest", "oldest"]
    ] = "newest"