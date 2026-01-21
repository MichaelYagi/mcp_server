"""
Location MCP Server
Runs over stdio transport
"""
import json
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP
from tools.location.geolocate_util import geolocate_ip, CLIENT_IP
from tools.location.get_location import get_location as get_location_fn
from tools.location.get_time import get_time as get_time_fn
from tools.location.get_weather import get_weather as get_weather_fn

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Create the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove any existing handlers (in case something already configured it)
root_logger.handlers.clear()

# Create formatter
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Create file handler
file_handler = logging.FileHandler(LOG_DIR / "mcp_location_server.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Add handlers to root logger
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Disable propagation to avoid duplicate logs
logging.getLogger("mcp").setLevel(logging.DEBUG)
logging.getLogger("mcp_location_server").setLevel(logging.INFO)

logger = logging.getLogger("mcp_location_server")
logger.info("🚀 Server logging initialized - writing to logs/mcp_location_server.log")

mcp = FastMCP("location-server")

@mcp.tool()
def get_location_tool(city: str | None = None, state: str | None = None, country: str | None = None) -> str:
    """
    Retrieve structured geographic information for any location.

    Args:
        city (str, optional): City name (e.g., "Surrey", "Tokyo")
        state (str, optional): State/province (e.g., "BC", "California", "Ontario")
        country (str, optional): Country name (e.g., "Canada", "Japan")

    All arguments are optional. If none provided, uses client's IP to determine location.
    Timezone is NEVER required - determined automatically.

    Returns:
        JSON string with:
        - city: City name
        - state: State/province/region
        - country: Country name
        - latitude: Geographic latitude
        - longitude: Geographic longitude
        - timezone: IANA timezone identifier
        - timezone_offset: UTC offset

    Use when user asks about where a place is, geographic context, or "my location".
    """
    logger.info(f"🛠 [server] get_location_tool called with city: {city}, state: {state}, country: {country}")
    if not city and CLIENT_IP:
        loc = geolocate_ip(CLIENT_IP)
        if loc:
            city = loc.get("city")
            state = loc.get("region")
            country = loc.get("country")

    return json.dumps(get_location_fn(city, state, country), indent=2)


@mcp.tool()
def get_time_tool(city: str | None = None, state: str | None = None, country: str | None = None) -> str:
    """
    Get the current local time for any city in the world.

    Args:
        city (str, optional): City name (e.g., "London", "New York")
        state (str, optional): State/province (e.g., "NY", "Queensland")
        country (str, optional): Country name (e.g., "United States", "Australia")

    All arguments are optional. If none provided, uses client's IP to determine location.
    Timezone is NEVER required - determined automatically from location.

    Returns:
        JSON string with:
        - city: City name
        - state: State/province
        - country: Country name
        - current_time: Current time in HH:MM:SS format
        - date: Current date in YYYY-MM-DD format
        - timezone: IANA timezone identifier
        - day_of_week: Day name (Monday, Tuesday, etc.)

    Use when user asks "What time is it in X" or "What time is it here".
    """
    logger.info(f"🛠 [server] get_time_tool called with city: {city}, state: {state}, country: {country}")
    if not city and CLIENT_IP:
        loc = geolocate_ip(CLIENT_IP)
        if loc:
            city = loc.get("city")
            state = loc.get("region")
            country = loc.get("country")

    return json.dumps(get_time_fn(city, state, country), indent=2)


@mcp.tool()
def get_weather_tool(city: str | None = None, state: str | None = None, country: str | None = None) -> str:
    """
    Get current weather conditions for any location.

    Args:
        city (str, optional): City name (e.g., "Surrey", "Paris")
        state (str, optional): State/province/prefecture (e.g., "BC", "California", "Kanagawa")
        country (str, optional): FULL country name (e.g., "Canada", "Japan", "United States")

    All arguments are optional. If none provided, uses client's IP to determine location.

    IMPORTANT: Never put a province/state into the country field.

    Returns:
        JSON string with:
        - location: {city, state, country}
        - current: {
            temperature_c: Current temperature in Celsius
            temperature_f: Current temperature in Fahrenheit
            condition: Weather description
            humidity: Humidity percentage
            wind_speed_kph: Wind speed
            feels_like_c: Feels like temperature
          }
        - forecast: Array of upcoming days with high/low temps

    Use when user asks about weather, temperature, or forecast.
    """
    logger.info(f"🛠 [server] get_weather_tool called with city: {city}, state: {state}, country: {country}")
    logger.info(f"🌤️  get_weather_tool called with: city={city}, state={state}, country={country}")
    logger.info(f"🌤️  CLIENT_IP = {CLIENT_IP}")

    if not city and CLIENT_IP:
        logger.info(f"🌤️  No city provided, using IP geolocation...")
        loc = geolocate_ip(CLIENT_IP)
        logger.info(f"🌤️  Geolocation result: {loc}")
        if loc:
            city = loc.get("city")
            state = loc.get("region")
            country = loc.get("country")
            logger.info(f"🌤️  Resolved to: city={city}, state={state}, country={country}")

    result = get_weather_fn(city, state, country)
    logger.info(f"🌤️  Result: {result}")
    logger.info(f"🌤️  Returning weather result")
    return result

if __name__ == "__main__":
    logger.info(f"🛠 [server] location-server running with stdio enabled")
    mcp.run(transport="stdio")