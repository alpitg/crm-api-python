from pydantic import BaseModel
from typing import Optional

class OrderStatusIn(BaseModel):
    code: str
    name: str
    description: Optional[str] = ""
    is_active: Optional[bool] = True

class OrderStatusOut(OrderStatusIn):
    id: str
