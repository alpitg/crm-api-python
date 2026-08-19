from pydantic import BaseModel
from typing import Optional

class OrderStatusIn(BaseModel):
    code: str
    name: str
    description: Optional[str] = ""
    isActive: Optional[bool] = True

class OrderStatusOut(OrderStatusIn):
    id: str
