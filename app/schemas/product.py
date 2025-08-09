from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class Discount(BaseModel):
    is_active: bool = False
    type: Optional[Literal["flat", "percentage"]] = None
    value: Optional[float] = None

class Deal(BaseModel):
    label: Optional[str] = None
    valid_till: Optional[datetime] = None

class ProductIn(BaseModel):
    name: str
    description: Optional[str]
    status: Literal["active", "draft", "archived"]
    inventory: int
    category: str
    base_cost: float
    mrp: float
    price: float
    totalWishlistedCount: int = 0
    discount: Optional[Discount] = Discount()
    deal: Optional[Deal] = Deal()
    product_type: Literal["simple", "customizable"] = "simple"

class ProductOut(ProductIn):
    id: str
