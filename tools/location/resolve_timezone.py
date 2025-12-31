from tools.location.get_time_data import CITY_TIMEZONES, COUNTRY_TIMEZONES, DEFAULT_TZ

def resolve_timezone(city: str, country: str) -> str:
    # Exact match first
    key = (city, country)
    if key in CITY_TIMEZONES:
        return CITY_TIMEZONES[key]

    # Country-level fallback
    if country in COUNTRY_TIMEZONES:
        return COUNTRY_TIMEZONES[country]

    # Final fallback
    return DEFAULT_TZ