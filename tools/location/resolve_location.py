from typing import Optional
from tools.location.detect_location import detect_default_location

def resolve_location(city: Optional[str], country: Optional[str]):
    """
    Normalizes location input and applies auto-detected defaults.
    """
    default_loc = detect_default_location()

    return {
        "city": city or default_loc["city"],
        "country": country or default_loc["country"]
    }
