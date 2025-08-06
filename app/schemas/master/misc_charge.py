from pydantic import BaseModel
from typing import Optional

class MiscChargeIn(BaseModel):
    code: str
    name: str
    cost: float
    description: Optional[str] = ""
    is_active: Optional[bool] = True

class MiscChargeOut(MiscChargeIn):
    id: str
