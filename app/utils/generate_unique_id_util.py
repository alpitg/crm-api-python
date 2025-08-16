import datetime
import random

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
