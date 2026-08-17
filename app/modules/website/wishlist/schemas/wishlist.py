from typing import Optional

from pydantic import BaseModel, Field


class WishlistIdentity(BaseModel):
    customerId: Optional[str] = None
    guestCartId: Optional[str] = None


class AddWishlistItemIn(WishlistIdentity):
    productId: str = Field(..., min_length=1)


class MergeWishlistIn(BaseModel):
    guestCartId: str = Field(..., min_length=1)
    customerId: str = Field(..., min_length=1)


class WishlistItemResponse(BaseModel):
    id: str
    productId: str
    customerId: Optional[str] = None
    guestCartId: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class WishlistResponse(BaseModel):
    id: Optional[str] = None
    customerId: Optional[str] = None
    guestCartId: Optional[str] = None
    items: list[dict] = []
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class WishlistMutationResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    item: Optional[dict] = None


class MergeWishlistResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    wishlist: Optional[dict] = None