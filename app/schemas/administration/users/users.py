from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.schemas.administration.organization_units.organization_units import OrganisationUnitOut
from app.schemas.administration.roles.roles import RoleOut


# ---------- Role ----------
class RoleIn(BaseModel):
    id: str
    name: Optional[str] = None
    displayName: Optional[str] = None
    description: Optional[str] = None
    isDefault: bool = False
    isStatic: bool = False
    isActive: bool = True
    creationTime: Optional[datetime] = None


# ---------- User ----------
class UserIn(BaseModel):
    userName: str
    name: str
    surname: str
    emailAddress: str
    isEmailConfirmed: bool = False
    isActive: bool = True
    phoneNumber: Optional[str] = None
    profilePictureId: Optional[str] = None
    lockoutEndDateUtc: Optional[datetime] = None


class UserOut(UserIn):
    id: str
    roles: List[RoleIn] = []
    creationTime: datetime


class UserRoleAssignment(BaseModel):
    roleId: str
    roleName: str
    roleDisplayName: str
    isAssigned: bool = False    
    inheritedFromOrganizationUnit: bool = False

# ---------- Wrapper with Permissions ----------
class UserWithPermissions(BaseModel):
    user: UserOut
    roles: List[RoleOut] = None
    memberedOrganizationUnits: List[str] = None
    allOrganizationUnits: List[OrganisationUnitOut] = None

    grantedPermissionNames: Optional[List[str]] = None
    permissions: Optional[List[str]] = None  # extend later if needed

# ---------- Pagination ----------
class PaginatedUsersOut(BaseModel):
    total: int
    page: int
    pageSize: int
    pages: int
    items: List[UserOut]

# --------- user-permission --------

class UserPermission(BaseModel):
    id: str
    grantedPermissionNames: List[str] = []

