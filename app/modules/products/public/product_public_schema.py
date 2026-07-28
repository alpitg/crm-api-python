from pydantic import BaseModel
from typing import List, Optional

from app.modules.products.schemas.product import MediaItem, Price

class PublicPrice(Price):
    currency: str = "INR"

class PublicProductOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    categories: List[str]
    tags: List[str]
    media: Optional[List[MediaItem]]
    price: PublicPrice
    status: str

class PaginatedProductsOut(BaseModel):
    total: int
    page: int
    pageSize: int
    pages: int
    items: List[PublicProductOut]