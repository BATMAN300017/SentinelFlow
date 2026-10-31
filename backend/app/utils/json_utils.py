import json
from decimal import Decimal
from datetime import datetime, date
from uuid import UUID
from typing import Any, Union

class CustomJSONEncoder(json.JSONEncoder):
    """Robust JSON encoder supporting Decimal, datetime, date, UUID, and AdaptiveRow."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if hasattr(obj, "_dict"):
            return dict(obj._dict)
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        return super().default(obj)

def safe_json_dumps(val: Any, default: Any = None, indent: int = None) -> str:
    """Safely dump data to JSON string handling Decimal, datetime, and custom objects."""
    try:
        return json.dumps(val, cls=CustomJSONEncoder, indent=indent)
    except Exception:
        return "{}" if default is None else str(default)

def safe_json_loads(val: Any, default: Any = None) -> Any:
    """Safely parse JSON data, handling already parsed dicts/lists from PostgreSQL JSONB."""
    if val is None:
        return {} if default is None else default
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, (str, bytes, bytearray)):
        try:
            return json.loads(val)
        except Exception:
            return {} if default is None else default
    return {} if default is None else default

def sanitize_json_dict(d: Any) -> Any:
    """Recursively converts Decimals and datetime objects in a dict/list to JSON-serializable primitives."""
    if isinstance(d, dict):
        return {k: sanitize_json_dict(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [sanitize_json_dict(v) for v in d]
    elif isinstance(d, Decimal):
        return float(d)
    elif isinstance(d, (datetime, date)):
        return d.isoformat()
    elif isinstance(d, UUID):
        return str(d)
    elif hasattr(d, "_dict"):
        return sanitize_json_dict(dict(d._dict))
    return d
