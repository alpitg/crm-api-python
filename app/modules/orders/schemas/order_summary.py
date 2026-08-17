from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class OrderSummaryOut(BaseModel):
    """
    Summary representation of an order for listing endpoints.
    """

    id: str
    orderCode: str
    customerName: str
    createdAt: Optional[datetime] = None
    itemCount: int = Field(..., ge=0)
    paymentStatus: Optional[str] = None
    total: float = Field(..., ge=0)
    orderStatus: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
    )


class PaginatedOrdersOut(BaseModel):
    """
    Paginated order summary response.
    """

    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    pageSize: int = Field(..., ge=1)
    pages: int = Field(..., ge=0)
    items: List[OrderSummaryOut] = Field(
        default_factory=list,
    )


class GetOrdersFilterIn(BaseModel):
    """
    Filters and pagination parameters for order listing.
    """

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
    ] = Field(
        default="newest",
        description="Sort orders by creation date",
    )