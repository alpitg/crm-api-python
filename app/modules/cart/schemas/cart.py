from pydantic import BaseModel, Field
from typing import Any


class CartItemIn(BaseModel):
    productId: str
    productType: str = "physical"
    quantity: int = Field(default=1, ge=1)
    customizedDetails: dict[str, Any] | None = None


# class CreateCartIn(BaseModel):
#     customerId: str | None = None
#     guestCartId: str | None = None


class AddCartItemIn(BaseModel):
    customerId: str | None = None
    guestCartId: str | None = None

    productId: str
    productType: str = "physical"
    quantity: int = Field(default=1, ge=1)
    customizedDetails: dict[str, Any] | None = None


class UpdateCartItemIn(BaseModel):
    customerId: str | None = None
    guestCartId: str | None = None

    productId: str
    quantity: int = Field(ge=1)
    customizedDetails: dict[str, Any] | None = None


class RemoveCartItemIn(BaseModel):
    customerId: str | None = None
    guestCartId: str | None = None

    productId: str


class ClearCartIn(BaseModel):
    customerId: str | None = None
    guestCartId: str | None = None


class MergeGuestCartIn(BaseModel):
    customerId: str
    guestCartId: str