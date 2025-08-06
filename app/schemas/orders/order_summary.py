from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class OrderSummaryOut(BaseModel):
    orderId: str = Field(..., alias="_id")
    customerName: str
    date: datetime
    itemCount: int
    paymentStatus: Literal["draft", "issued", "paid"]
    total: float
    orderStatus: Literal["pending", "fulfilled", "partial", "cancelled"]

    class Config:
        populate_by_name = True
