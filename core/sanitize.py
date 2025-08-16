
from typing import TypeVar
from bson import ObjectId
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


def stringify_object_ids(obj):
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            # Convert `_id` to `id`
            key = "id" if k == "_id" else k
            new_obj[key] = stringify_object_ids(v)
        return new_obj
    elif isinstance(obj, list):
        return [stringify_object_ids(i) for i in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj
