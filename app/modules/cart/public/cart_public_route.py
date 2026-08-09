from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from datetime import datetime, timezone
from uuid import uuid4

from app.db.mongo import db
from app.modules.cart.schemas.cart import (
    AddCartItemIn,
    MergeGuestCartIn,
    UpdateCartItemIn,
    RemoveCartItemIn,
    ClearCartIn,
)

router = APIRouter()

cart_collection = db["carts"]
products_collection = db["products"]


# ============================================================
# Helpers
# ============================================================

def utc_now():
    return datetime.now(timezone.utc)


def is_valid_object_id(value: str) -> bool:
    return ObjectId.is_valid(value)


def get_cart_owner_query(
    customer_id: str | None = None,
    guest_cart_id: str | None = None,
):
    """
    A cart can belong to either:

    Logged-in customer:
        {
            "customerId": "...",
            "guestCartId": None
        }

    Guest:
        {
            "guestCartId": "...",
            "customerId": None
        }

    customerId has priority if both are supplied.
    """

    if customer_id:
        return {
            "customerId": customer_id,
            "guestCartId": None,
        }

    if guest_cart_id:
        return {
            "guestCartId": guest_cart_id,
            "customerId": None,
        }

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="customerId or guestCartId is required.",
    )


def validate_cart_owner(
    customer_id: str | None = None,
    guest_cart_id: str | None = None,
):
    """
    Exactly one cart owner must be supplied.
    """

    if not customer_id and not guest_cart_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="customerId or guestCartId is required.",
        )

    if customer_id and guest_cart_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either customerId or guestCartId, not both.",
        )


def validate_quantity(quantity: int):
    if quantity < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be at least 1.",
        )

    if quantity > 999:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity cannot exceed 999.",
        )


async def get_product(product_id: str):
    if not product_id or not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID.",
        )

    product = await products_collection.find_one(
        {
            "_id": ObjectId(product_id),
            "status": "published",
        }
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return product


def get_product_price(product: dict) -> float:
    price = product.get("price") or {}

    return float(
        price.get("sellingPrice")
        or price.get("price")
        or 0
    )

def get_product_discount(product: dict) -> dict:
    price = product.get("price") or {}

    return price.get("discount") or {}

def get_product_mrp(product: dict) -> float:
    price = product.get("price") or {}

    return float(
        price.get("mrp")
        or price.get("basePrice")
        or price.get("sellingPrice")
        or price.get("price")
        or 0
    )


# ============================================================
# Cart Response
# ============================================================

async def build_cart_response(cart: dict | None):
    """
    Always calculate pricing from current product data.

    Frontend is NOT the source of truth for:
        - MRP
        - selling price
        - discount
        - tax
        - shipping
        - misc charges
        - grand total
    """

    if not cart:
        return {
            "id": None,
            "customerId": None,
            "guestCartId": None,
            "items": [],
            "summary": {
                "totalItems": 0,
                "totalQuantity": 0,
                "mrp": 0,
                "discount": 0,
                "subtotal": 0,
                "shipping": 0,
                "tax": 0,
                "miscCharges": 0,
                "grandTotal": 0,
            },
        }

    response_items = []

    mrp_total = 0
    subtotal = 0
    total_quantity = 0

    for item in cart.get("items", []):
        product_id = item.get("productId")

        if not product_id:
            continue

        try:
            product = await get_product(product_id)
        except HTTPException:
            # Product may have been unpublished/deleted
            # after being added to the cart.
            continue

        selling_price = get_product_price(product)
        mrp = get_product_mrp(product)

        quantity = int(item.get("quantity", 1))

        if quantity < 1:
            continue

        item_mrp = mrp * quantity
        item_subtotal = selling_price * quantity

        item_discount = get_product_discount(product)

        mrp_total += item_mrp
        subtotal += item_subtotal
        total_quantity += quantity

        media = product.get("media") or []

        image = None

        if media and isinstance(media[0], dict):
            image = media[0].get("url")

        response_items.append(
            {
                "productId": product_id,
                "productType": item.get(
                    "productType",
                    "physical",
                ),
                "quantity": quantity,
                "name": product.get("name"),
                "description": product.get(
                    "description"
                ),
                "image": image,
                "price": {
                    "mrp": mrp,
                    "sellingPrice": selling_price,
                    "discount": item_discount,
                },
                "itemTotal": item_subtotal,
                "customizedDetails": item.get(
                    "customizedDetails"
                ),
            }
        )

    # --------------------------------------------------------
    # Discount
    # --------------------------------------------------------

    discount = max(
        mrp_total - subtotal,
        0,
    )

    # --------------------------------------------------------
    # Business rules
    #
    # These can later come from:
    # - shipping service
    # - tax service
    # - coupon service
    # - misc charge service
    # --------------------------------------------------------

    shipping = 0
    tax = 0
    misc_charges = 0

    grand_total = (
        subtotal
        + shipping
        + tax
        + misc_charges
    )

    return {
        "id": str(cart["_id"]),

        "customerId": cart.get(
            "customerId"
        ),

        "guestCartId": cart.get(
            "guestCartId"
        ),

        "items": response_items,

        "summary": {
            "totalItems": len(response_items),

            "totalQuantity": total_quantity,

            "mrp": round(
                mrp_total,
                2,
            ),

            "discount": round(
                discount,
                2,
            ),

            "subtotal": round(
                subtotal,
                2,
            ),

            "shipping": round(
                shipping,
                2,
            ),

            "tax": round(
                tax,
                2,
            ),

            "miscCharges": round(
                misc_charges,
                2,
            ),

            "grandTotal": round(
                grand_total,
                2,
            ),
        },
    }


# ============================================================
# Find Cart
# ============================================================

async def find_cart(
    customer_id: str | None = None,
    guest_cart_id: str | None = None,
):
    query = get_cart_owner_query(
        customer_id=customer_id,
        guest_cart_id=guest_cart_id,
    )

    return await cart_collection.find_one(query)


# ============================================================
# Create Empty Cart
# ============================================================

async def create_cart(
    customer_id: str | None = None,
    guest_cart_id: str | None = None,
):
    validate_cart_owner(
        customer_id=customer_id,
        guest_cart_id=guest_cart_id,
    )

    now = utc_now()

    cart = {
        "customerId": customer_id,
        "guestCartId": guest_cart_id,

        "items": [],

        "createdAt": now,
        "updatedAt": now,
    }

    result = await cart_collection.insert_one(
        cart
    )

    cart["_id"] = result.inserted_id

    return cart


# ============================================================
# GET /create
# ============================================================

@router.get("/create")
async def get_or_create_cart(
    customerId: str | None = None,
    guestCartId: str | None = None,
):
    """
    Get or create a cart.

    Logged-in customer:

        GET /cart/create?customerId=xxxxx

    Guest:

        GET /cart/create?guestCartId=xxxxx

    First-time guest:

        GET /cart/create

    In the last case a guestCartId is generated and
    returned to the frontend.
    """

    # --------------------------------------------------------
    # Both supplied
    # --------------------------------------------------------

    if customerId and guestCartId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either customerId or guestCartId, not both.",
        )

    # --------------------------------------------------------
    # First-time guest
    # --------------------------------------------------------

    if not customerId and not guestCartId:
        guestCartId = str(uuid4())

    # --------------------------------------------------------
    # Find existing cart
    # --------------------------------------------------------

    cart = await find_cart(
        customer_id=customerId,
        guest_cart_id=guestCartId,
    )

    # --------------------------------------------------------
    # Create if missing
    # --------------------------------------------------------

    if not cart:
        cart = await create_cart(
            customer_id=customerId,
            guest_cart_id=guestCartId,
        )

    return await build_cart_response(cart)


# ============================================================
# POST /add-item
# ============================================================

@router.post(
    "/add-item",
    status_code=status.HTTP_200_OK,
)
async def add_cart_item(
    payload: AddCartItemIn,
):
    """
    Add product to cart.

    If product already exists:

        existing quantity + requested quantity

    Example:

        Cart quantity = 2
        Request quantity = 1

        Result = 3
    """

    validate_cart_owner(
        customer_id=payload.customerId,
        guest_cart_id=payload.guestCartId,
    )

    validate_quantity(
        payload.quantity
    )

    # --------------------------------------------------------
    # Validate product
    # --------------------------------------------------------

    product = await get_product(
        payload.productId
    )

    # --------------------------------------------------------
    # Validate price
    # --------------------------------------------------------

    price = get_product_price(product)

    if price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product price is invalid.",
        )

    # --------------------------------------------------------
    # Find cart
    # --------------------------------------------------------

    cart = await find_cart(
        customer_id=payload.customerId,
        guest_cart_id=payload.guestCartId,
    )

    # --------------------------------------------------------
    # Create cart if required
    # --------------------------------------------------------

    if not cart:
        cart = await create_cart(
            customer_id=payload.customerId,
            guest_cart_id=payload.guestCartId,
        )

    items = cart.get("items", [])

    # --------------------------------------------------------
    # Find existing item
    # --------------------------------------------------------

    existing_item = None

    for item in items:
        if (
            item.get("productId")
            == payload.productId
        ):
            existing_item = item
            break

    # --------------------------------------------------------
    # Existing item
    # --------------------------------------------------------

    if existing_item:

        new_quantity = (
            int(existing_item.get("quantity", 0))
            + payload.quantity
        )

        validate_quantity(
            new_quantity
        )

        existing_item["quantity"] = (
            new_quantity
        )

        if payload.customizedDetails is not None:
            existing_item[
                "customizedDetails"
            ] = payload.customizedDetails

    # --------------------------------------------------------
    # New item
    # --------------------------------------------------------

    else:

        items.append(
            {
                "productId": payload.productId,

                "productType": (
                    payload.productType
                    or "physical"
                ),

                "quantity": payload.quantity,

                "customizedDetails": (
                    payload.customizedDetails
                ),
            }
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    await cart_collection.update_one(
        {
            "_id": cart["_id"],
        },
        {
            "$set": {
                "items": items,
                "updatedAt": utc_now(),
            }
        },
    )

    # --------------------------------------------------------
    # Return fresh cart
    # --------------------------------------------------------

    updated_cart = await cart_collection.find_one(
        {
            "_id": cart["_id"],
        }
    )

    return await build_cart_response(
        updated_cart
    )


# ============================================================
# PUT /update-item
# ============================================================

@router.put(
    "/update-item",
    status_code=status.HTTP_200_OK,
)
async def update_cart_item(
    payload: UpdateCartItemIn,
):
    """
    Set exact quantity.

    Example:

        quantity = 3

    means:

        item.quantity = 3
    """

    validate_cart_owner(
        customer_id=payload.customerId,
        guest_cart_id=payload.guestCartId,
    )

    validate_quantity(
        payload.quantity
    )

    # --------------------------------------------------------
    # Find cart
    # --------------------------------------------------------

    cart = await find_cart(
        customer_id=payload.customerId,
        guest_cart_id=payload.guestCartId,
    )

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found.",
        )

    items = cart.get("items", [])

    # --------------------------------------------------------
    # Find item
    # --------------------------------------------------------

    found = False

    for item in items:

        if (
            item.get("productId")
            == payload.productId
        ):

            # Validate product still exists
            await get_product(
                payload.productId
            )

            item["quantity"] = (
                payload.quantity
            )

            if payload.customizedDetails is not None:
                item[
                    "customizedDetails"
                ] = payload.customizedDetails

            found = True
            break

    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product is not present in cart.",
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    await cart_collection.update_one(
        {
            "_id": cart["_id"],
        },
        {
            "$set": {
                "items": items,
                "updatedAt": utc_now(),
            }
        },
    )

    # --------------------------------------------------------
    # Return fresh cart
    # --------------------------------------------------------

    updated_cart = await cart_collection.find_one(
        {
            "_id": cart["_id"],
        }
    )

    return await build_cart_response(
        updated_cart
    )


# ============================================================
# DELETE /remove-item
# ============================================================

@router.delete(
    "/remove-item",
    status_code=status.HTTP_200_OK,
)
async def remove_cart_item(
    payload: RemoveCartItemIn,
):
    validate_cart_owner(
        customer_id=payload.customerId,
        guest_cart_id=payload.guestCartId,
    )

    # --------------------------------------------------------
    # Find cart
    # --------------------------------------------------------

    cart = await find_cart(
        customer_id=payload.customerId,
        guest_cart_id=payload.guestCartId,
    )

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found.",
        )

    items = cart.get("items", [])

    # --------------------------------------------------------
    # Remove item
    # --------------------------------------------------------

    new_items = [
        item
        for item in items
        if item.get("productId")
        != payload.productId
    ]

    if len(new_items) == len(items):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product is not present in cart.",
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    await cart_collection.update_one(
        {
            "_id": cart["_id"],
        },
        {
            "$set": {
                "items": new_items,
                "updatedAt": utc_now(),
            }
        },
    )

    # --------------------------------------------------------
    # Return fresh cart
    # --------------------------------------------------------

    updated_cart = await cart_collection.find_one(
        {
            "_id": cart["_id"],
        }
    )

    return await build_cart_response(
        updated_cart
    )


# ============================================================
# DELETE /clear
# ============================================================

@router.delete(
    "/clear",
    status_code=status.HTTP_200_OK,
)
async def clear_cart(
    payload: ClearCartIn,
):
    validate_cart_owner(
        customer_id=payload.customerId,
        guest_cart_id=payload.guestCartId,
    )

    # --------------------------------------------------------
    # Find cart
    # --------------------------------------------------------

    cart = await find_cart(
        customer_id=payload.customerId,
        guest_cart_id=payload.guestCartId,
    )

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found.",
        )

    # --------------------------------------------------------
    # Clear
    # --------------------------------------------------------

    await cart_collection.update_one(
        {
            "_id": cart["_id"],
        },
        {
            "$set": {
                "items": [],
                "updatedAt": utc_now(),
            }
        },
    )

    # --------------------------------------------------------
    # Return fresh cart
    # --------------------------------------------------------

    updated_cart = await cart_collection.find_one(
        {
            "_id": cart["_id"],
        }
    )

    return await build_cart_response(
        updated_cart
    )


# ============================================================
# POST /merge
# ============================================================

@router.post(
    "/merge",
    status_code=status.HTTP_200_OK,
)
async def merge_guest_cart(
    payload: MergeGuestCartIn,
):
    """
    Merge a guest cart into a logged-in customer's cart.

    Example:

        Guest:
            A x 2
            B x 1

        Customer:
            A x 1
            C x 3

        Result:

            A x 3
            B x 1
            C x 3

    After successful merge, the guest cart is deleted.
    """

    if not payload.customerId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="customerId is required.",
        )

    if not payload.guestCartId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="guestCartId is required.",
        )

    if (
        payload.customerId
        == payload.guestCartId
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="customerId and guestCartId cannot be the same.",
        )

    # --------------------------------------------------------
    # Find guest cart
    # --------------------------------------------------------

    guest_cart = await cart_collection.find_one(
        {
            "guestCartId": payload.guestCartId,
            "customerId": None,
        }
    )

    # --------------------------------------------------------
    # If guest cart doesn't exist
    # simply return customer cart.
    # --------------------------------------------------------

    if not guest_cart:

        customer_cart = await find_cart(
            customer_id=payload.customerId
        )

        if not customer_cart:
            customer_cart = await create_cart(
                customer_id=payload.customerId,
                guest_cart_id=None,
            )

        return await build_cart_response(
            customer_cart
        )

    # --------------------------------------------------------
    # Find customer cart
    # --------------------------------------------------------

    customer_cart = await find_cart(
        customer_id=payload.customerId
    )

    # --------------------------------------------------------
    # Customer has no cart
    # Move guest items directly
    # --------------------------------------------------------

    if not customer_cart:

        now = utc_now()

        customer_cart = {
            "customerId": payload.customerId,
            "guestCartId": None,

            "items": guest_cart.get(
                "items",
                [],
            ),

            "createdAt": now,
            "updatedAt": now,
        }

        result = await cart_collection.insert_one(
            customer_cart
        )

        customer_cart["_id"] = (
            result.inserted_id
        )

    # --------------------------------------------------------
    # Customer already has cart
    # --------------------------------------------------------

    else:

        customer_items = customer_cart.get(
            "items",
            []
        )

        guest_items = guest_cart.get(
            "items",
            []
        )

        # ----------------------------------------------------
        # Merge items
        # ----------------------------------------------------

        for guest_item in guest_items:

            guest_product_id = (
                guest_item.get(
                    "productId"
                )
            )

            guest_quantity = int(
                guest_item.get(
                    "quantity",
                    0,
                )
            )

            if not guest_product_id:
                continue

            if guest_quantity <= 0:
                continue

            existing_item = next(
                (
                    item
                    for item in customer_items
                    if item.get("productId")
                    == guest_product_id
                ),
                None,
            )

            # -----------------------------------------------
            # Same product
            # -----------------------------------------------

            if existing_item:

                new_quantity = (
                    int(
                        existing_item.get(
                            "quantity",
                            0,
                        )
                    )
                    + guest_quantity
                )

                validate_quantity(
                    new_quantity
                )

                existing_item[
                    "quantity"
                ] = new_quantity

                # Keep guest customization only
                # if customer item doesn't have one.
                if (
                    not existing_item.get(
                        "customizedDetails"
                    )
                    and guest_item.get(
                        "customizedDetails"
                    )
                ):
                    existing_item[
                        "customizedDetails"
                    ] = guest_item.get(
                        "customizedDetails"
                    )

            # -----------------------------------------------
            # New product
            # -----------------------------------------------

            else:

                customer_items.append(
                    {
                        "productId": guest_product_id,

                        "productType": (
                            guest_item.get(
                                "productType",
                                "physical",
                            )
                        ),

                        "quantity": guest_quantity,

                        "customizedDetails": (
                            guest_item.get(
                                "customizedDetails"
                            )
                        ),
                    }
                )

        # ----------------------------------------------------
        # Save customer cart
        # ----------------------------------------------------

        await cart_collection.update_one(
            {
                "_id": customer_cart["_id"],
            },
            {
                "$set": {
                    "items": customer_items,
                    "updatedAt": utc_now(),
                }
            },
        )

    # --------------------------------------------------------
    # Delete guest cart
    # --------------------------------------------------------

    await cart_collection.delete_one(
        {
            "_id": guest_cart["_id"]
        }
    )

    # --------------------------------------------------------
    # Return final customer cart
    # --------------------------------------------------------

    updated_cart = await cart_collection.find_one(
        {
            "_id": customer_cart["_id"]
        }
    )

    return await build_cart_response(
        updated_cart
    )