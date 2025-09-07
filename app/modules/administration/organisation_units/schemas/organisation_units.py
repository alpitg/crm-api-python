from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class GetOrganisationUnitsFilterIn(BaseModel):
    page: int = 1
    pageSize: int = 10
    searchText: Optional[str] = None
    sort: Optional[str] = "newest"  # newest | oldest


class OrganisationUnitOut(BaseModel):
    id: str
    parentId: Optional[str]
    code: Optional[str] = None
    displayName: str
    memberCount: Optional[int] = None
    roleCount: Optional[int] = None
    creationTime: Optional[datetime] = None
    creatorUserId: Optional[int] = None
    lastModificationTime: Optional[str] = None
    lastModifierUserId: Optional[int] = None
    isDeleted: Optional[bool] = False

class PaginatedOrganisationUnitsOut(BaseModel):
    total: int
    page: int
    pageSize: int
    pages: int
    items: list[OrganisationUnitOut]

class OrganisationUnitIn(BaseModel):
    parentId: Optional[str] = None
    code: Optional[str] = None
    displayName: str
    memberCount: int = 0
    roleCount: int = 0
    creatorUserId: Optional[int] = None


class OrganisationUnitOut(OrganisationUnitIn):
    id: str
    creationTime: Optional[datetime] = None
    lastModificationTime: Optional[datetime] = None
    lastModifierUserId: Optional[int] = None


class  GetOrganizationUnitsParamsAssignRole(GetOrganisationUnitsFilterIn): 
    isAssigned: bool = None

class AddRolesToOrganisationUnitIn(BaseModel):
    roleIds: List[str]   
    organizationUnitId: str
    
class DeleteRolesToOrganisationUnitIn(BaseModel):
    roleId: str  
    organizationUnitId: str
    