from pydantic import BaseModel
from typing import List, Literal, Optional
from datetime import datetime

class OrderSummaryOut(BaseModel):
    id: str
    orderCode: str
    customerName: str
    createdAt: Optional[datetime]
    itemCount: int
    paymentStatus: Optional[str] # Literal["pending", "paid", "failed", "refunded"] # case-sensitive
    total: float
    orderStatus: Optional[str] # Literal["pending", "fulfilled", "partial", "cancelled"]

    class Config:
        populate_by_name = True

class PaginatedOrdersOut(BaseModel):
    total: int
    page: int
    pageSize: int
    pages: int
    items: List[OrderSummaryOut]

from pydantic import BaseModel, Field
from typing import Optional

class GetOrdersFilterIn(BaseModel):
    customerName: Optional[str] = Field(None, description="Filter orders by customer name (partial match)")
    orderCode: Optional[str] = Field(None, description="Filter orders by order code (exact or partial match)")
    page: int = Field(1, ge=1, description="Page number (1-based)")
    pageSize: int = Field(10, ge=1, le=100, description="Number of results per page")
    sort: Optional[Literal["newest", "oldest"]] = "newest"
