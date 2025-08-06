from pydantic import BaseModel
from typing import Optional

class GlassTypeIn(BaseModel):
    name: str
    rate: float
    rateIn: str
    is_active: Optional[bool] = True

class GlassTypeOut(GlassTypeIn):
    id: str
