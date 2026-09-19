import json
from typing import Any


def serialize_output_value(value: Any) -> Any:
    """Convert structured values into readable, portable output values."""
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return value
