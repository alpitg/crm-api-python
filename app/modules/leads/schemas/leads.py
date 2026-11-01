from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ---------- Status ----------
class LeadStatus(str, Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    proposal = "proposal"
    won = "won"
    lost = "lost"


# ---------- Lead ----------
class LeadIn(BaseModel):
    name: str
    company: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    source: Optional[str] = None  # e.g. "website", "referral", "instagram"
    status: LeadStatus = LeadStatus.new
    value: float = 0  # expected deal value
    owner: Optional[str] = None  # assigned sales person
    quoteDetails: Optional[str] = None  # details of the quote requested
    description: Optional[str] = None
    isActive: bool = True


class LeadOut(LeadIn):
    id: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


# ---------- Pagination ----------
class GetLeadsParams(BaseModel):
    page: Optional[int] = Field(default=1, ge=1)
    pageSize: Optional[int] = Field(default=10, ge=1, le=100)
    searchText: Optional[str] = None
    status: Optional[LeadStatus] = None
    sort: Optional[str] = None  # e.g. "createdAt desc"


class PaginatedLeads(BaseModel):
    total: int
    page: int
    pageSize: int
    pages: int
    items: List[LeadOut]