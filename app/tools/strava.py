import requests


def get_recent_activities(
    access_token: str,
    per_page: int = 40,
) -> list:
    """
    Fetch recent running activities from Strava.
    """

    per_page = min(per_page, 100)

    resp = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        params={
            "per_page": per_page,
            "page": 1,
        },
        timeout=10,
    )

    resp.raise_for_status()

    activities = resp.json()
    runs = []

    for act in activities:
        if act.get("type") not in ("Run", "VirtualRun"):
            continue

        distance_km = round(act.get("distance", 0) / 1000, 2)
        duration_minutes = round(act.get("moving_time", 0) / 60, 1)

        pace_min_per_km = (
            round(duration_minutes / distance_km, 2)
            if distance_km > 0
            else None
        )

        runs.append({
            "strava_id": act.get("id"),
            "name": act.get("name", "Run"),
            "date": act.get("start_date_local"),
            "distance_km": distance_km,
            "duration_minutes": duration_minutes,
            "pace_min_per_km": pace_min_per_km,
            "elevation_gain_m": act.get("total_elevation_gain", 0),
            "average_heartrate": act.get("average_heartrate"),
            "max_heartrate": act.get("max_heartrate"),
        })

    return runs