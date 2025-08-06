from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class OrderSummaryOut(BaseModel):
    orderId: str
    customerName: str
    date: datetime
    itemCount: int
    paymentStatus: Literal["pending", "paid", "failed", "refunded"] # case-sensitive
    total: float
    orderStatus: Literal["pending", "fulfilled", "partial", "cancelled"]

    class Config:
        populate_by_name = True
