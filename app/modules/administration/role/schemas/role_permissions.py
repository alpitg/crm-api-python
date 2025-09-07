from pydantic import BaseModel
from typing import Optional

class RolePermissionBase(BaseModel):
    name: str
    displayName: str
    description: Optional[str] = None
    parentName: Optional[str] = None
    isGrantedByDefault: bool = False

class RolePermissionIn(RolePermissionBase):
    pass

class RolePermissionOut(RolePermissionBase):
    id: str
