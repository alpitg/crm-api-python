from typing import Any

from app.modules.products.schemas.product import ProductIn


def _get_price(product: ProductIn) -> dict[str, Any]:
    return product.get("price") or {}


def get_product_mrp(product: ProductIn) -> float:
    """
    Return UNIT MRP.

    Priority:
        mrp
        basePrice
        sellingPrice
        price
    """
    price = _get_price(product)

    return float(
        price.get("mrp")
        or price.get("basePrice")
        or price.get("sellingPrice")
        or price.get("price")
        or 0
    )


def get_product_selling_price(product: ProductIn) -> float:
    """
    Return UNIT selling price.

    Priority:
        sellingPrice
        price
        basePrice
    """
    price = _get_price(product)

    return float(
        price.get("sellingPrice")
        or price.get("price")
        or price.get("basePrice")
        or 0
    )


def get_product_discount(product: ProductIn) -> dict[str, Any]:
    """
    Return configured product discount.
    """
    price = _get_price(product)
    discount = price.get("discount") or {}

    return {
        "isActive": bool(
            discount.get("isActive", False)
        ),
        "type": discount.get("type", "none"),
        "value": float(
            discount.get("value") or 0
        ),
    }


def get_product_tax(product: ProductIn) -> dict[str, Any]:
    """
    Return configured product tax.
    """
    price = _get_price(product)
    tax = price.get("tax") or {}

    return {
        "rate": float(
            tax.get("rate") or 0
        ),
        "included": bool(
            tax.get("included", False)
        ),
        "className": tax.get("className"),
    }


def get_product_pricing(
    product: ProductIn,
    quantity: int = 1,
) -> dict[str, Any]:
    """
    Calculate pricing for a cart/order line.

    All monetary values are calculated from UNIT prices.

    Returns:

        mrp
            Total MRP for the requested quantity.

        unitMrp
            UNIT MRP.

        sellingPrice
            Total selling price for the requested quantity.

        unitSellingPrice
            UNIT selling price.

        subtotal
            Selling price * quantity.

        discount
            MRP total - subtotal.

        taxAmount
            Total tax, including tax already included
            in the selling price.

        excludedTaxAmount
            Only tax that needs to be added to subtotal.

        grandTotal
            subtotal + excludedTaxAmount.
    """

    if quantity < 1:
        raise ValueError(
            "Quantity must be at least 1."
        )

    mrp = get_product_mrp(product)
    selling_price = get_product_selling_price(product)

    if selling_price <= 0:
        raise ValueError(
            "Invalid selling price."
        )

    # If MRP isn't configured, use selling price.
    if mrp <= 0:
        mrp = selling_price

    # MRP should never be lower than selling price.
    if mrp < selling_price:
        mrp = selling_price

    tax = get_product_tax(product)

    tax_rate = tax["rate"]
    tax_included = tax["included"]

    # --------------------------------------------------------
    # Line totals
    # --------------------------------------------------------

    mrp_total = mrp * quantity

    subtotal = selling_price * quantity

    discount_amount = max(
        mrp_total - subtotal,
        0.0,
    )

    # --------------------------------------------------------
    # Tax
    # --------------------------------------------------------

    tax_amount = 0.0

    if tax_rate > 0:

        if tax_included:
            # Selling price already includes tax.
            tax_amount = (
                subtotal
                - (
                    subtotal
                    / (1 + tax_rate / 100)
                )
            )

        else:
            # Tax must be added to subtotal.
            tax_amount = (
                subtotal
                * tax_rate
                / 100
            )

    tax_amount = round(
        tax_amount,
        2,
    )

    excluded_tax_amount = (
        tax_amount
        if not tax_included
        else 0.0
    )

    grand_total = round(
        subtotal
        + excluded_tax_amount,
        2,
    )

    return {
        # ----------------------------------------------------
        # MRP
        # ----------------------------------------------------

        "mrp": round(
            mrp_total,
            2,
        ),

        "unitMrp": round(
            mrp,
            2,
        ),

        # ----------------------------------------------------
        # Selling price
        # ----------------------------------------------------

        "sellingPrice": round(
            subtotal,
            2,
        ),

        "unitSellingPrice": round(
            selling_price,
            2,
        ),

        "quantity": quantity,

        # ----------------------------------------------------
        # Discount
        # ----------------------------------------------------

        "discount": round(
            discount_amount,
            2,
        ),

        # ----------------------------------------------------
        # Subtotal
        # ----------------------------------------------------

        "subtotal": round(
            subtotal,
            2,
        ),

        # ----------------------------------------------------
        # Tax
        # ----------------------------------------------------

        "tax": {
            "className": tax["className"],
            "rate": tax_rate,
            "included": tax_included,
            "amount": tax_amount,
        },

        "taxAmount": tax_amount,

        "excludedTaxAmount": round(
            excluded_tax_amount,
            2,
        ),

        # ----------------------------------------------------
        # Final
        # ----------------------------------------------------

        "grandTotal": grand_total,
    }


def calculate_item_pricing(
    product: ProductIn,
    quantity: int,
) -> dict[str, Any]:
    """
    Backward-compatible alias.
    """
    return get_product_pricing(
        product,
        quantity,
    )