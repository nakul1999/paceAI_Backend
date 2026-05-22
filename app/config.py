import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REDIRECT_URI = os.getenv(
    "STRAVA_REDIRECT_URI",
    "http://localhost:8000/auth/strava/callback"
)

DEFAULT_CITY = "Dublin,IE"
DEFAULT_LAT = 53.3498
DEFAULT_LON = -6.2603