import json
import os
import requests
from typing import Optional
from tools.location.resolve_location import resolve_location
from dotenv import load_dotenv

def get_weather(city: Optional[str] = None, state: Optional[str] = None, country: Optional[str] = None) -> str:
    """
    Fetches real weather data using WeatherAPI.com.
    Falls back to a clear error message if the API key is missing or the request fails.
    When parsing locations:
    • City = city name (e.g., Surrey)
    • State = province or prefecture or state (e.g., BC, Ontario, Kanagawa, California)
    • Country = full country name (e.g., Canada, Japan, United States)

    Never put a province or state into the country field.
    """
    loc = resolve_location(city, state, country)

    load_dotenv()
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return json.dumps({
            "error": "missing_api_key",
            "message": "Set WEATHER_API_KEY in your environment to enable real weather data.",
            "city": loc["city"],
            "state": loc["state"],
            "country": loc["country"]
        }, indent=2)

    # WeatherAPI expects "City,State,Country"
    query_parts = [loc['city'], loc['state'], loc['country']]
    query = ",".join([p for p in query_parts if p])
    url = f"https://api.weatherapi.com/v1/forecast.json?key={api_key}&q={query}&aqi=no&days=1"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        # WeatherAPI error format
        if "error" in data:
            return json.dumps({
                "error": data["error"].get("code"),
                "message": data["error"].get("message"),
                "city": loc["city"],
                "state": loc["state"],
                "country": loc["country"]
            }, indent=2)

        location = data["location"]
        current = data["current"]
        forecast = data["forecast"]

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🌤️  get_weather called with: city={city}, state={state}, country={country}")
        logger.info(f"🌤️  {url}")

        result = {
            "city": location["name"],
            "state": location["region"],
            "country": location["country"],
            "weather": {
                "condition": current["condition"]["text"],
                "temperature_f": current["temp_f"],
                "temperature_c": current["temp_c"],
                "feelslike_f": current["feelslike_f"],
                "feelslike_c": current["feelslike_c"],
                "humidity": current["humidity"],
                "maxtemp_f": forecast["forecastday"][0]["day"]["maxtemp_f"],
                "maxtemp_c": forecast["forecastday"][0]["day"]["maxtemp_c"],
                "mintemp_f": forecast["forecastday"][0]["day"]["mintemp_f"],
                "mintemp_c": forecast["forecastday"][0]["day"]["mintemp_c"]
            }
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "error": "request_failed",
            "message": str(e),
            "city": loc["city"],
            "state": loc["state"],
            "country": loc["country"]
        }, indent=2)
