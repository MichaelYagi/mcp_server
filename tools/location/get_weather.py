import json
import os
import requests
from typing import Optional
from tools.location.resolve_location import resolve_location
from dotenv import load_dotenv

def get_weather(city: Optional[str] = None, country: Optional[str] = None) -> str:
    """
    Fetches real weather data using WeatherAPI.com.
    Falls back to a clear error message if the API key is missing or the request fails.
    """
    loc = resolve_location(city, country)

    load_dotenv()
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return json.dumps({
            "error": "missing_api_key",
            "message": "Set WEATHER_API_KEY in your environment to enable real weather data.",
            "city": loc["city"],
            "country": loc["country"]
        }, indent=2)

    # WeatherAPI expects "City,Country"
    query = f"{loc['city']},{loc['country']}"
    url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={query}&aqi=no"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        # WeatherAPI error format
        if "error" in data:
            return json.dumps({
                "error": data["error"].get("code"),
                "message": data["error"].get("message"),
                "city": loc["city"],
                "country": loc["country"]
            }, indent=2)

        current = data["current"]

        result = {
            "city": loc["city"],
            "country": loc["country"],
            "weather": {
                "condition": current["condition"]["text"],
                "temperature_c": current["temp_c"],
                "humidity": current["humidity"]
            }
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "error": "request_failed",
            "message": str(e),
            "city": loc["city"],
            "country": loc["country"]
        }, indent=2)
