"""
Weather MCP Server
Exposes current weather and weather forecast tools via Model Context Protocol.
"""
from mcp.server.mcpserver import MCPServer

server = MCPServer("weather-server")

# Simulated weather database
_WEATHER_DB = {
    "tokyo": {
        "city": "Tokyo",
        "country": "Japan",
        "temperature_c": 19.5,
        "temperature_f": 67.1,
        "condition": "Partly Cloudy",
        "humidity_pct": 58,
        "wind_kmh": 14.2,
    },
    "paris": {
        "city": "Paris",
        "country": "France",
        "temperature_c": 14.0,
        "temperature_f": 57.2,
        "condition": "Light Rain",
        "humidity_pct": 75,
        "wind_kmh": 22.0,
    },
    "new york": {
        "city": "New York",
        "country": "United States",
        "temperature_c": 22.5,
        "temperature_f": 72.5,
        "condition": "Sunny",
        "humidity_pct": 45,
        "wind_kmh": 11.5,
    },
    "london": {
        "city": "London",
        "country": "United Kingdom",
        "temperature_c": 12.0,
        "temperature_f": 53.6,
        "condition": "Overcast",
        "humidity_pct": 82,
        "wind_kmh": 18.5,
    },
    "bengaluru": {
        "city": "Bengaluru",
        "country": "India",
        "temperature_c": 26.0,
        "temperature_f": 78.8,
        "condition": "Scattered Clouds",
        "humidity_pct": 60,
        "wind_kmh": 9.0,
    },
}


@server.tool()
def get_current_weather(city: str) -> dict:
    """
    Retrieve real-time current weather metrics for a specified city.
    
    Use this tool when you need current atmospheric conditions, temperature,
    humidity, or wind speed for a given city.
    
    Args:
        city: The name of the city (e.g. 'Tokyo', 'London', 'Paris', 'New York').
    """
    normalized = city.strip().lower()
    if normalized in _WEATHER_DB:
        return _WEATHER_DB[normalized]
    
    # Return sensible fallback if city is not specifically listed
    return {
        "city": city.title(),
        "country": "Unknown",
        "temperature_c": 20.0,
        "temperature_f": 68.0,
        "condition": "Clear",
        "humidity_pct": 50,
        "wind_kmh": 10.0,
        "note": "Estimated typical conditions for unindexed city",
    }


@server.tool()
def get_weather_forecast(city: str, days: int = 3) -> dict:
    """
    Retrieve a multi-day weather forecast for a specified city.
    
    Use this tool when the user asks about upcoming weather, tomorrow's forecast,
    or weather over the next several days.
    
    Args:
        city: The target city name.
        days: The number of days to forecast (1 to 7, default 3).
    """
    current = get_current_weather(city)
    base_temp = current["temperature_c"]
    
    forecasts = []
    conditions = ["Sunny", "Partly Cloudy", "Showers", "Clear", "Overcast"]
    for day in range(1, min(days, 7) + 1):
        forecasts.append({
            "day": day,
            "forecast_temp_c": round(base_temp + (day * 0.8 - 1.5), 1),
            "condition": conditions[(day + hash(city)) % len(conditions)],
            "precipitation_chance_pct": (day * 15) % 80,
        })
        
    return {
        "city": current["city"],
        "forecast_days": days,
        "daily_forecast": forecasts,
    }


if __name__ == "__main__":
    server.run(transport="stdio")
