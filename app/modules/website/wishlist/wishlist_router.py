from fastapi import APIRouter, HTTPException, Query, status

from app.modules.website.wishlist.schemas.wishlist import (
    AddWishlistItemIn,
    MergeWishlistIn,
)
from app.modules.website.wishlist.services.wishlist_service import (
    WishlistServiceError,
    wishlist_service,
)



router = APIRouter()


@router.get("")
async def get_wishlist(
    customerId: str | None = Query(default=None),
    guestCartId: str | None = Query(default=None),
):
    """
    Get the website wishlist.

    Authenticated user:
        ?customerId=...

    Guest user:
        ?guestCartId=...
    """
    try:
        return await wishlist_service.get_wishlist(
            customer_id=customerId,
            guest_cart_id=guestCartId,
        )

    except WishlistServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/items",
    status_code=status.HTTP_201_CREATED,
)
async def add_wishlist_item(
    payload: AddWishlistItemIn,
):
    """
    Add a product to the website wishlist.

    Authenticated:
        {
            "customerId": "...",
            "productId": "..."
        }

    Guest:
        {
            "guestCartId": "...",
            "productId": "..."
        }
    """
    try:
        return await wishlist_service.add_item(
            product_id=payload.productId,
            customer_id=payload.customerId,
            guest_cart_id=payload.guestCartId,
        )

    except WishlistServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete("/items/{productId}")
async def remove_wishlist_item(
    productId: str,
    customerId: str | None = Query(default=None),
    guestCartId: str | None = Query(default=None),
):
    """
    Remove a product from the website wishlist.
    """
    try:
        return await wishlist_service.remove_item(
            product_id=productId,
            customer_id=customerId,
            guest_cart_id=guestCartId,
        )

    except WishlistServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/merge")
async def merge_guest_wishlist(
    payload: MergeWishlistIn,
):
    """
    Merge a guest wishlist into the authenticated customer's
    wishlist after login.
    """
    try:
        return await wishlist_service.merge_guest_wishlist(
            guest_cart_id=payload.guestCartId,
            customer_id=payload.customerId,
        )

    except WishlistServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc