import datetime
import random
import re

def to_capital_snake_case(name: str) -> str:
    # Remove non-alphanumeric characters, replace with underscore
    name = re.sub(r'[^A-Za-z0-9]+', '_', name)
    # Uppercase and strip leading/trailing underscores
    return name.upper().strip('_')

def generate_role_code(display_name: str) -> str:
    """
    Example: PRODUCT_MANAGER-20250823-49301
    """
    role_name = to_capital_snake_case(display_name)
    return role_name

def generate_order_code() -> str:
    """
    Example: ORD-20250812-49301
    """
    today = datetime.datetime.now().strftime("%Y%m%d")  # e.g., 20250812
    rand = random.randint(10000, 99999)                 # 5-digit random
    return f"ORD-{today}-{rand}"

def generate_product_code() -> str:
    """
    Example: PRD-20250812-49301
    """
    today = datetime.datetime.now().strftime("%Y%m%d")  # e.g., 20250812
    rand = random.randint(10000, 99999)                 # 5-digit random
    return f"PRD-{today}-{rand}"
