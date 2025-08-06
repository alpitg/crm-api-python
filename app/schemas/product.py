from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

#region sample json

# {
#   "name": "Abstract Sunset",
#   "category": "Canvas Painting",
#   "inventory": 10,
#   "base_cost": 1500,
#   "mrp": 2500,
#   "price": 2300,
#   "status": "active",
#   "product_type": "customizable",
#   "customization": {
#     "is_customizable": true,
#     "frame": {
#       "type": "box",
#       "color": "black",
#       "width_in_inch": 12,
#       "height_in_inch": 18,
#       "cost_per_sq_inch": 1.5
#     },
#     "glass": {
#       "type": "acrylic",
#       "cost_per_sq_inch": 0.7
#     },
#     "moulding": {
#       "type": "classic",
#       "cost_per_inch": 0.5
#     }
#   },
#   "discount": {
#     "is_active": true,
#     "type": "percentage",
#     "value": 10
#   }
# }

#endregion

#region customized options

class FrameDetails(BaseModel):
    type: str
    color: Optional[str]
    width_in_inch: float
    height_in_inch: float
    cost_per_sq_inch: float

class GlassDetails(BaseModel):
    type: str
    thickness: Optional[str]
    cost_per_sq_inch: float

class MouldingDetails(BaseModel):
    type: str
    profile: Optional[str]
    cost_per_inch: float

class CustomizationOptions(BaseModel):
    is_customizable: bool = False
    frame: Optional[FrameDetails]
    glass: Optional[GlassDetails]
    moulding: Optional[MouldingDetails]

#endregion

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
    customization: Optional[CustomizationOptions] = None

class ProductOut(ProductIn):
    id: str
