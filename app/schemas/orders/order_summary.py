from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

class OrderSummaryOut(BaseModel):
    id: str
    customerName: str
    createdAt: Optional[datetime]
    itemCount: int
    paymentStatus: Literal["pending", "paid", "failed", "refunded"] # case-sensitive
    total: float
    orderStatus: Literal["pending", "fulfilled", "partial", "cancelled"]

    class Config:
        populate_by_name = True
