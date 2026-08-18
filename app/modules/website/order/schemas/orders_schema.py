from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class WebsiteOrderItemResponse(BaseModel):
    productId: str
    productType: str
    name: str
    description: Optional[str] = None
    quantity: int
    unitPrice: float
    mrp: float
    discountAmount: float = 0
    taxAmount: float = 0
    cancelledQty: int = 0


class WebsiteDeliveryAddressResponse(BaseModel):
    name: Optional[str] = None
    mobile: Optional[str] = None
    addressType: Optional[str] = None
    addressLine1: Optional[str] = None
    addressLine2: Optional[str] = None
    landmark: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


class WebsiteOrderResponse(BaseModel):
    id: str
    orderCode: str
    customerName: Optional[str] = None

    items: list[WebsiteOrderItemResponse] = []

    deliveryAddress: Optional[WebsiteDeliveryAddressResponse] = None

    paymentMethod: Optional[str] = None
    paymentStatus: Optional[str] = None
    orderStatus: Optional[str] = None

    subtotal: float = 0
    shippingAmount: float = 0
    totalDiscountAmount: float = 0
    totalTaxAmount: float = 0
    totalAmount: float = 0
    cancelledAmount: float = 0

    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class WebsiteOrderPagination(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class WebsiteOrdersResponse(BaseModel):
    success: bool
    orders: list[WebsiteOrderResponse]
    pagination: WebsiteOrderPagination