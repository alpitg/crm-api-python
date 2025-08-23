from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ---------- Filter ----------
class GetRolesFilterIn(BaseModel):
    page: int = 1
    pageSize: int = 10
    searchText: Optional[str] = None
    sort: Optional[str] = "newest"  # newest | oldest


# ---------- Base Input ----------
class RoleIn(BaseModel):
    name: str
    displayName: str
    description: Optional[str] = None
    code: Optional[str] = None
    isDefault: bool = False
    isStatic: bool = False
    iaActive: Optional[bool] = True
    creatorUserId: Optional[str] = None


# ---------- Output ----------
class RoleOut(RoleIn):
    id: str
    creationTime: Optional[datetime] = None
    lastModificationTime: Optional[datetime] = None
    lastModifierUserId: Optional[int] = None
    isDeleted: Optional[bool] = False


# ---------- Paginated ----------
class PaginatedRolesOut(BaseModel):
    total: int
    page: int
    pageSize: int
    pages: int
    items: List[RoleOut]
