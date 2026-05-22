import requests
from datetime import datetime

from app.config import OPENWEATHER_API_KEY, DEFAULT_CITY


def get_current_weather(city: str = DEFAULT_CITY, units: str = "metric") -> dict:
    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": units,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        return {
            "city": data["name"],
            "country": data.get("sys", {}).get("country"),
            "temperature_c": round(data["main"]["temp"], 1),
            "feels_like_c": round(data["main"]["feels_like"], 1),
            "humidity_pct": data["main"]["humidity"],
            "wind_speed_kmh": round(data["wind"]["speed"] * 3.6, 1),
            "wind_direction_deg": data["wind"].get("deg", 0),
            "description": data["weather"][0]["description"],
            "visibility_km": round(data.get("visibility", 10000) / 1000, 1),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    except Exception as e:
        return {"error": str(e)}