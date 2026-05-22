from app.tools.weather import get_current_weather
from app.tools.strava import get_recent_activities
from app.tools.acwr import calculate_acwr_from_activities


def recommend_training_today(
    access_token: str,
    city: str = "Dublin,IE",
    per_page: int = 40,
) -> dict:
    weather = get_current_weather(city=city)

    activities = get_recent_activities(
        access_token=access_token,
        per_page=per_page,
    )

    acwr_result = calculate_acwr_from_activities(activities)

    temp = weather.get("temperature_c", 15)
    wind = weather.get("wind_speed_kmh", 0)
    humidity = weather.get("humidity_pct", 50)

    current_acwr = acwr_result.get("current_acwr")

    recommendation = "Easy Run"
    duration = "40–60 min"
    intensity = "Zone 2"
    rationale = []

    if current_acwr is None:
        rationale.append("Not enough training history for a reliable ACWR calculation.")
    elif current_acwr > 1.5:
        recommendation = "Rest Day"
        duration = "0–20 min walk or mobility"
        intensity = "Recovery only"
        rationale.append("ACWR is above 1.5, suggesting high workload risk.")
    elif current_acwr > 1.3:
        recommendation = "Recovery Run"
        duration = "20–40 min"
        intensity = "Zone 1–2"
        rationale.append("ACWR is elevated, so avoid hard training today.")
    elif current_acwr < 0.8:
        recommendation = "Easy Run"
        duration = "30–45 min"
        intensity = "Zone 2"
        rationale.append("Training load is currently low, so a controlled easy run is suitable.")
    else:
        rationale.append("ACWR is within the optimal training range.")

    if wind > 35:
        recommendation = "Indoor Session"
        duration = "30–45 min"
        intensity = "Easy aerobic"
        rationale.append("Wind speed is high, so outdoor quality running is not ideal.")

    if humidity > 85:
        rationale.append("High humidity may increase perceived effort.")

    if temp < 3:
        rationale.append("Cold conditions require a longer warm-up.")

    if temp <= 5:
        clothing = ["Long-sleeve base layer", "Running jacket", "Gloves", "Light hat"]
    elif temp <= 12:
        clothing = ["Long sleeve or light jacket", "Tights or shorts"]
    elif temp <= 18:
        clothing = ["T-shirt", "Shorts", "Optional light layer"]
    else:
        clothing = ["Lightweight top", "Shorts", "Hydration recommended"]

    return {
        "recommendation": recommendation,
        "recommended_duration": duration,
        "recommended_intensity": intensity,
        "rationale": rationale,
        "clothing": clothing,
        "weather": weather,
        "acwr": acwr_result,
        "runs_used": len(activities),
    }