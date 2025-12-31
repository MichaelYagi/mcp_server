import json
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Optional
from tools.location.resolve_location import resolve_location
from tools.location.resolve_timezone import resolve_timezone
from tools.location.get_time_data import DEFAULT_TZ

def get_time(
    city: Optional[str] = None,
    country: Optional[str] = None,
    timezone: Optional[str] = None
) -> str:
    loc = resolve_location(city, country)

    # Determine timezone
    tz_name = timezone or resolve_timezone(loc["city"], loc["country"])

    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo(DEFAULT_TZ)
        tz_name = DEFAULT_TZ

    now = datetime.now(tz)

    result = {
        "city": loc["city"],
        "country": loc["country"],
        "timezone": tz_name,
        "local_time": now.isoformat()
    }

    return json.dumps(result, indent=2)
