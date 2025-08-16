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
    basePrice: Optional[float] = Field(ge=0)
    discountType: Optional[DiscountType] = "none"
    discountPercentage: Optional[float] = Field(default=None, ge=0, le=100)
    fixedDiscountedPrice: Optional[float] = Field(default=None, ge=0)
    taxClass: Optional[TaxClass] = "tax_free"
    vatPercent: Optional[float] = Field(default=None, ge=0, le=100)

class Inventory(BaseModel):
    sku: Optional[str] = None
    barcode: Optional[str] = None
    quantityInShelf: Optional[int] = Field(default=0, ge=0)
    quantityInWarehouse: Optional[int] = Field(default=0, ge=0)
    quantity: Optional[int] = Field(default=0, ge=0)  # will be set in __init__
    allowBackorders: bool = False

    def __init__(self, **data):
        super().__init__(**data)
        object.__setattr__(self, 'quantity', (self.quantityInShelf or 0) + (self.quantityInWarehouse or 0))

class Variation(BaseModel):
    name: Literal["color", "size", "material", "style"]
    values: List[str] = Field(default_factory=list)

class Shipping(BaseModel):
    isPhysical: bool = True
    weightInKg: Optional[float] = Field(default=None, ge=0)
    lengthInCm: Optional[float] = Field(default=None, ge=0)
    widthInCm: Optional[float] = Field(default=None, ge=0)
    heightInCm: Optional[float] = Field(default=None, ge=0)

class Meta(BaseModel):
    metaTitle: Optional[str] = None
    metaDescription: Optional[str] = None
    metaKeywords: List[str] = Field(default_factory=list, description="Comma-split on the FE")

class Scheduling(BaseModel):
    publishAt: Optional[datetime] = None

# -------- Primary models --------
class ProductBase(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProductStatus] = "draft"
    template: Optional[ProductTemplate] = "default"
    categories: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    media: List[MediaItem] = Field(default_factory=list)
    price: Optional[Price] = None
    totalWishlistedCount: Optional[float] = None
    inventory: Inventory = Inventory()
    variations: List[Variation] = Field(default_factory=list)
    shipping: Shipping = Shipping()
    meta: Meta = Meta()
    scheduling: Scheduling = Scheduling()
    rating: Optional[int] = None

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
    createdAt: datetime
    updatedAt: datetime

    @staticmethod
    def from_in(id: str, data: ProductIn) -> "ProductOut":
        now = datetime.now(timezone.utc)
        return ProductOut(id=id, createdAt=now, updatedAt=now, **data.model_dump())
    
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
