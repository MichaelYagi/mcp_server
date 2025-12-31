import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from tools.location.resolve_location import resolve_location

CITY_TIMEZONES = {
    ("Surrey", "Canada"): "America/Vancouver",
    ("Vancouver", "Canada"): "America/Vancouver",
    ("Toronto", "Canada"): "America/Toronto",
    ("New York", "USA"): "America/New_York",
    ("London", "UK"): "Europe/London",
    ("Tokyo", "Japan"): "Asia/Tokyo",
}

DEFAULT_TZ = "America/Vancouver"

def get_time(city: Optional[str] = None, country: Optional[str] = None) -> str:
    loc = resolve_location(city, country)
    key = (loc["city"], loc["country"])

    tz_name = CITY_TIMEZONES.get(key, DEFAULT_TZ)
    now = datetime.now(ZoneInfo(tz_name))

    result = {
        "city": loc["city"],
        "country": loc["country"],
        "timezone": tz_name,
        "local_time": now.isoformat()
    }

    return json.dumps(result, indent=2)
