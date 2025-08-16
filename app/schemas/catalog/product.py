from typing import List, Optional, Literal
from fastapi import Query
from pydantic import BaseModel, Field
from datetime import datetime, timezone

# -------- Enums / Literals --------
ProductStatus = Literal["published", "draft", "scheduled", "inactive"]
DiscountType = Literal["none", "percentage", "fixed"]
TaxClass = Literal["tax_free", "taxable_goods", "downloadable_product"]
ProductTemplate = Literal["default", "electronics", "office_stationary", "fashion"]

# -------- Sub-models --------
class MediaItem(BaseModel):
    url: Optional[str] = None
    alt: Optional[str] = None

class Price(BaseModel):
    base_price: float = Field(ge=0)
    discount_type: DiscountType = "none"
    discount_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    fixed_discounted_price: Optional[float] = Field(default=None, ge=0)
    tax_class: TaxClass = "taxable_goods"
    vat_percent: Optional[float] = Field(default=None, ge=0, le=100)

class Inventory(BaseModel):
    sku: Optional[str] = None
    barcode: Optional[str] = None
    quantity: int = Field(default=0, ge=0)
    allow_backorders: bool = False

class Variation(BaseModel):
    name: Literal["color", "size", "material", "style"]
    values: List[str] = Field(default_factory=list)

class Shipping(BaseModel):
    is_physical: bool = True
    weight_kg: Optional[float] = Field(default=None, ge=0)
    length_cm: Optional[float] = Field(default=None, ge=0)
    width_cm: Optional[float] = Field(default=None, ge=0)
    height_cm: Optional[float] = Field(default=None, ge=0)

class Meta(BaseModel):
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: List[str] = Field(default_factory=list, description="Comma-split on the FE")

class Scheduling(BaseModel):
    publish_at: Optional[datetime] = None

# -------- Primary models --------
class ProductBase(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    status: ProductStatus = "draft"
    template: ProductTemplate = "default"
    categories: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    media: List[MediaItem] = Field(default_factory=list)
    price: Price
    totalWishlistedCount: Optional[float] = None
    inventory: Inventory = Inventory()
    variations: List[Variation] = Field(default_factory=list)
    shipping: Shipping = Shipping()
    meta: Meta = Meta()
    scheduling: Scheduling = Scheduling()

class ProductIn(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProductStatus] = None
    template: Optional[ProductTemplate] = None
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    media: Optional[List[MediaItem]] = None
    price: Optional[Price] = None
    inventory: Optional[Inventory] = None
    variations: Optional[List[Variation]] = None
    shipping: Optional[Shipping] = None
    meta: Optional[Meta] = None
    scheduling: Optional[Scheduling] = None

class ProductOut(ProductBase):
    id: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_in(id: str, data: ProductIn) -> "ProductOut":
        now = datetime.now(timezone.utc)
        return ProductOut(id=id, created_at=now, updated_at=now, **data.model_dump())
    
class PaginatedProductsOut(BaseModel):
    total: int
    page: int
    pageSize: int
    pages: int
    items: List[ProductOut]

class GetProductsFilterIn(BaseModel):
    searchText: Optional[str] = Query(default=None, description="Search in name or code or tags"),
    # status: Optional[str] = Query(default=None, description="Filter by status"),
    page: int = Field(1, ge=1, description="Page number (1-based)")
    pageSize: int = Field(10, ge=1, le=100, description="Number of results per page")
    sort: Optional[Literal["newest", "oldest"]] = "newest"
