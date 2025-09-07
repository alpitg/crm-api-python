from typing import Optional

from pydantic import BaseModel

class FrameTypeIn(BaseModel):
    name: str
    description: Optional[str] = None
    base_cost_per_sqin: Optional[float] = 0.0
    category: Optional[str] = None
    is_active: bool = True

class FrameTypeOut(FrameTypeIn):
    id: str
