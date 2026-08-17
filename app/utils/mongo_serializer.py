from datetime import date, datetime
from typing import Any

from bson import ObjectId


def serialize_mongo(value: Any) -> Any:
    """
    Convert MongoDB/Python values into JSON-safe values.

    ObjectId -> str
    datetime -> ISO string
    dict/list/tuple -> recursively serialized
    """

    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: serialize_mongo(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            serialize_mongo(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            serialize_mongo(item)
            for item in value
        ]

    return value