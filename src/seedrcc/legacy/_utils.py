from datetime import datetime
from typing import Any, Optional


def parse_datetime(dt_str: Optional[Any]) -> Optional[datetime]:
    """Parse datetime strings or unix timestamps from the API.

    Returns None if the input is invalid or None.
    """
    if not dt_str:
        return None
    try:
        if isinstance(dt_str, (int, float)):
            return datetime.fromtimestamp(dt_str)
        return datetime.strptime(str(dt_str), "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None
