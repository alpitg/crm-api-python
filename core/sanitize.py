
from typing import TypeVar
from pydantic import BaseModel
T = TypeVar("T", bound=BaseModel)

def sanitize_input(data: dict) -> dict:
    """
    Recursively convert empty strings to None.
    """
    for key, value in data.items():
        if isinstance(value, dict):
            data[key] = sanitize_input(value)
        elif isinstance(value, list):
            data[key] = [sanitize_input(v) if isinstance(v, dict) else (None if v == "" else v) for v in value]
        elif value == "":
            data[key] = None
    return data
