from typing import Any, Dict, Optional

def clean_text(value: Any) -> str:
    """
    Normalize text fields from the Instagram payload.

    - Converts None to empty string.
    - Strips leading/trailing whitespace.
    """
    if value is None:
        return ""
    text = str(value)
    return text.strip()

def ensure_int(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to int:

    - None or empty strings result in the default.
    - Invalid values (e.g. 'foo') also result in the default.
    """
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def build_location_data(
    city_name: Optional[Any],
    latitude: Optional[Any],
    longitude: Optional[Any],
) -> Dict[str, Any]:
    """
    Create a location_data structure consistent with the README schema.
    """
    def to_float(val: Any) -> float:
        if val is None or val == "":
            return 0.0
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    return {
        "city_name": clean_text(city_name),
        "latitude": to_float(latitude),
        "longitude": to_float(longitude),
    }