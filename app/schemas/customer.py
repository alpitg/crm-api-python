from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ---------- Address ----------
class Address(BaseModel):
    id: Optional[str] = None
    label: Optional[str] = None  # e.g. "home", "office", "other"
    addressLine1: Optional[str] = None
    addressLine2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postcode: Optional[str] = None
    country: Optional[str] = None
    isDefault: Optional[bool] = False


# ---------- Customer ----------
class CustomerIn(BaseModel):
    name: str
    email: Optional[str] = None
    description: Optional[str] = None
    addresses: List[Address] = []
    shippingAddress: Optional[Address] = None
    billingAddress: Optional[Address] = None
    isActive: bool = True


class CustomerOut(CustomerIn):
    id: str
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


# ---------- Pagination ----------
class GetCustomersParams(BaseModel):
    page: Optional[int] = 1
    pageSize: Optional[int] = 10
    searchText: Optional[str] = None
    status: Optional[str] = None
    sort: Optional[str] = None


class PaginatedCustomers(BaseModel):
    total: int
    page: int
    pageSize: int
    pages: int
    items: List[CustomerOut]
