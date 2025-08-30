from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.schemas.administration.organisation_units.organisation_units import OrganisationUnitOut
from app.schemas.administration.roles.roles import RoleIn, RoleOut


# ---------- Filter ----------
class GetUsersFilterIn(BaseModel):
    page: int = 1
    pageSize: int = 10
    searchText: Optional[str] = None
    sort: Optional[str] = "newest"  # newest | oldest


# ---------- User ----------
class UserIn(BaseModel):
    userName: str
    name: str
    surname: str
    emailAddress: str
    isEmailConfirmed: bool = False
    password: Optional[str] = None
    isActive: bool = True
    phoneNumber: Optional[str] = None
    profilePictureId: Optional[str] = None
    lockoutEndDateUtc: Optional[datetime] = None
    setRandomPassword: bool = False
    shouldChangePasswordOnNextLogin: bool = False
    sendActivationEmail: bool = False
    isLockoutEnabled: bool = False
    isDarkMode: Optional[bool] = False

class UserOut(UserIn):
    id: str
    roles: Optional[List[RoleIn]] = []
    creationTime: Optional[datetime] = None


class UserRoleAssignment(BaseModel):
    roleId: str
    roleName: str
    roleDisplayName: str
    isAssigned: bool = False    
    inheritedFromOrganizationUnit: bool = False

# ---------- Wrapper with Permissions ----------

class UserWithPermissionsIn(BaseModel):
    user: UserIn
    grantedRoles: List[str] = []
    roles: List[RoleIn] = []
    memberedOrganisationUnits: List[str] = []
    allOrganizationUnits: List[OrganisationUnitOut] = []
    grantedPermissionNames: Optional[List[str]] = []
    permissions: Optional[List[str]] = []

class UserWithPermissionsOut(BaseModel):
    user: UserOut
    grantedRoles: List[RoleOut] = []
    roles: List[RoleOut] = []
    memberedOrganisationUnits: List[str] = []
    allOrganizationUnits: List[OrganisationUnitOut] = []
    grantedPermissionNames: Optional[List[str]] = []
    permissions: Optional[List[str]] = []


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


# change password
class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str

# update profile
class UpdateUserProfileRequest(BaseModel):
    name: Optional[str]
    surname: Optional[str]
    emailAddress: Optional[str]
    userName: Optional[str]
   