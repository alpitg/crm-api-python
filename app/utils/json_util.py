import json


def to_json(data):
    if hasattr(data, "model_dump"):
        return json.dumps(data.model_dump(), indent=2)

    return json.dumps(data, indent=2)