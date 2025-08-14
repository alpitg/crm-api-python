from pydantic import BaseModel
from typing import Optional
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
