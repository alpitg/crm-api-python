from typing import Optional

def calculate_selling_price(price: dict) -> Optional[float]:
    if not price:
        return None

    base_price = price.get("basePrice")

    if base_price is None:
        return None

    discount = price.get("discount") or {}

    if not discount.get("isActive", False):
        return float(base_price)

    discount_type = discount.get("type")
    discount_value = discount.get("value") or 0

    if discount_type == "percentage":
        selling_price = base_price - (base_price * discount_value / 100)

    elif discount_type == "fixed":
        selling_price = max(base_price - discount_value, 0)

    else:
        selling_price = base_price

    return round(selling_price, 2)