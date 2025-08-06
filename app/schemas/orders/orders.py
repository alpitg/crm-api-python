from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class OrderItemIn(BaseModel):
    productId: str
    description: str
    quantity: int
    unitPrice: float
    discountedQuantity: Optional[int] = 0
    discountAmount: float = 0.0
    discountPercentage: float = 0.0
    cancelledQty: Optional[int] = 0

class OrderIn(BaseModel):
    customerId: str
    status: str = "pending"
    items: List[OrderItemIn]
    note: Optional[str] = ""

class OrderOut(OrderIn):
    id: str
    createdAt: datetime
    subtotal: float
    totalDiscountAmount: float
    totalAmount: float
    cancelledAmount: float
