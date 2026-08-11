from typing import Any

from app.modules.products.schemas.product import ProductIn, ProductTax


def get_product_mrp(product: ProductIn) -> float:
    price = product.get("price") or {}

    return float(
        price.get("mrp")
        or price.get("basePrice")
        or price.get("sellingPrice")
        or price.get("price")
        or 0
    )


def get_product_selling_price(product: ProductIn) -> float:
    price = product.get("price") or {}

    return float(
        price.get("sellingPrice")
        or price.get("basePrice")
        or price.get("price")
        or 0
    )


def get_product_discount(product: ProductIn) -> dict:
    price = product.get("price") or {}

    discount = price.get("discount") or {}

    return {
        "isActive": bool(discount.get("isActive", False)),
        "type": discount.get("type", "none"),
        "value": float(discount.get("value") or 0),
    }


def get_product_tax(product: ProductIn) -> ProductTax:
    price = product.get("price") or {}

    tax = price.get("tax") or {}

    return {
        "rate": float(tax.get("rate") or 0),
        "included": bool(tax.get("included", False)),
        "className": tax.get("className"),
    }


def calculate_item_pricing(
    product: dict,
    quantity: int,
) -> dict[str, Any]:
    """
    Calculate all pricing for one product line.

    Rules:
    - basePrice/MRP is used only for MRP and discount calculation.
    - sellingPrice is the actual product selling price.
    - If tax is included, sellingPrice already contains tax.
    - If tax is excluded, tax is added on top of sellingPrice.
    """

    if quantity < 1:
        raise ValueError(
            "Quantity must be greater than zero"
        )

    mrp = get_product_mrp(product)
    selling_price = get_product_selling_price(product)

    if selling_price <= 0:
        raise ValueError(
            f"Invalid selling price for {product.get('name')}"
        )

    # ==================================================
    # DISCOUNT
    # ==================================================

    discount_per_unit = max(
        mrp - selling_price,
        0,
    )

    discount_amount = (
        discount_per_unit * quantity
    )

    # ==================================================
    # SUBTOTAL
    # ==================================================

    subtotal = (
        selling_price * quantity
    )

    # ==================================================
    # TAX
    # ==================================================

    tax = get_product_tax(product)

    tax_rate = tax["rate"]
    tax_included = tax["included"]

    tax_amount = 0.0

    if tax_rate > 0:
        if tax_included:
            # Selling price already contains tax.
            tax_amount = (
                subtotal
                - (
                    subtotal
                    / (1 + tax_rate / 100)
                )
            )
        else:
            # Tax is added on top of selling price.
            tax_amount = (
                subtotal
                * tax_rate
                / 100
            )

    # ==================================================
    # TOTAL
    # ==================================================

    excluded_tax = (
        0.0
        if tax_included
        else tax_amount
    )

    total = (
        subtotal
        + excluded_tax
    )

    return {
        "mrp": round(mrp, 2),
        "sellingPrice": round(
            selling_price,
            2,
        ),
        "quantity": quantity,
        "discount": {
            "amount": round(
                discount_amount,
                2,
            ),
            "perUnit": round(
                discount_per_unit,
                2,
            ),
        },
        "subtotal": round(
            subtotal,
            2,
        ),
        "tax": {
            "rate": tax_rate,
            "included": tax_included,
            "className": tax["className"],
            "amount": round(
                tax_amount,
                2,
            ),
        },
        "excludedTax": round(
            excluded_tax,
            2,
        ),
        "total": round(
            total,
            2,
        ),
    }


from typing import Any


def get_product_pricing(product: dict[str, Any], quantity: int = 1) -> dict[str, Any]:
    price = product.get("price") or {}

    base_price = float(
        price.get("basePrice")
        or price.get("mrp")
        or price.get("sellingPrice")
        or 0
    )

    selling_price = float(
        price.get("sellingPrice")
        or price.get("price")
        or 0
    )

    if selling_price <= 0:
        raise ValueError("Invalid selling price")

    if base_price <= 0:
        base_price = selling_price

    quantity = int(quantity)

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")

    tax = price.get("tax") or {}

    tax_rate = float(tax.get("rate") or 0)
    tax_included = bool(tax.get("included", False))
    tax_class_name = tax.get("className")

    mrp_total = base_price * quantity
    subtotal = selling_price * quantity

    discount = max(
        mrp_total - subtotal,
        0,
    )

    tax_amount = 0.0

    if tax_rate > 0:
        if tax_included:
            tax_amount = (
                subtotal
                - (
                    subtotal
                    / (1 + tax_rate / 100)
                )
            )
        else:
            tax_amount = (
                subtotal
                * tax_rate
                / 100
            )

    tax_amount = round(tax_amount, 2)

    tax_snapshot = {
        "className": tax_class_name,
        "rate": tax_rate,
        "included": tax_included,
        "amount": tax_amount,
    }

    return {
        "mrp": round(mrp_total, 2),
        "unitMrp": round(base_price, 2),
        "sellingPrice": round(selling_price, 2),
        "unitSellingPrice": round(selling_price, 2),
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "tax": tax_snapshot,
        "taxAmount": tax_amount,
        "excludedTaxAmount": (
            tax_amount
            if not tax_included
            else 0.0
        ),
        "grandTotal": round(
            subtotal
            + (
                tax_amount
                if not tax_included
                else 0
            ),
            2,
        ),
    }