from pydantic import BaseModel
from typing import Optional

class MountTypeIn(BaseModel):
    code: str
    name: str
    cost: float
    description: Optional[str] = ""
    is_active: Optional[bool] = True

class MountTypeOut(MountTypeIn):
    id: str
