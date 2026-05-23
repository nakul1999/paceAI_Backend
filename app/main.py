from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.db import Base, engine, get_db
from app.database import models

from app.tools.weather import get_current_weather
from app.tools.strava import get_recent_activities
from app.tools.acwr import calculate_acwr_from_activities
from app.tools.recommendation import recommend_training_today

from app.services.strava_oauth import (
    get_strava_auth_url,
    exchange_code_for_token,
)
from app.services.token_service import get_latest_access_token
from app.agents.paceai_agent import run_paceai_agent
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="PaceAI Backend")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    user_id: int


@app.get("/")
def root():
    return {
        "message": "PaceAI backend is running"
    }


@app.get("/auth/strava/login")
def strava_login():
    auth_url = get_strava_auth_url()
    return RedirectResponse(auth_url)


@app.get("/auth/strava/callback")
def strava_callback(code: str, db: Session = Depends(get_db)):
    token_data = exchange_code_for_token(code)

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_at = token_data.get("expires_at")
    athlete = token_data.get("athlete", {})

    if not access_token or not athlete:
        raise HTTPException(
            status_code=400,
            detail="Failed to retrieve Strava token or athlete data",
        )

    strava_athlete_id = str(athlete.get("id"))

    user = (
        db.query(models.User)
        .filter(models.User.strava_athlete_id == strava_athlete_id)
        .first()
    )

    if not user:
        user = models.User(
            strava_athlete_id=strava_athlete_id,
            firstname=athlete.get("firstname"),
            lastname=athlete.get("lastname"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = models.StravaToken(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )

    db.add(token)
    db.commit()

    frontend_url = f"{FRONTEND_URL}/auth/callback?user_id={user.id}"
    return RedirectResponse(frontend_url)


@app.get("/weather")
def weather(city: str = "Dublin,IE"):
    return get_current_weather(city=city)


@app.get("/activities")
def activities(
    user_id: int,
    per_page: int = 40,
    db: Session = Depends(get_db),
):
    access_token = get_latest_access_token(db, user_id)

    if not access_token:
        raise HTTPException(
            status_code=404,
            detail="No Strava token found for this user",
        )

    runs = get_recent_activities(
        access_token=access_token,
        per_page=per_page,
    )

    return {
        "total_runs": len(runs),
        "activities": runs,
    }


@app.get("/acwr")
def acwr(
    user_id: int,
    per_page: int = 40,
    db: Session = Depends(get_db),
):
    access_token = get_latest_access_token(db, user_id)

    if not access_token:
        raise HTTPException(
            status_code=404,
            detail="No Strava token found for this user",
        )

    activities_data = get_recent_activities(
        access_token=access_token,
        per_page=per_page,
    )

    return calculate_acwr_from_activities(activities_data)


@app.get("/recommendation/today")
def today_recommendation(
    user_id: int,
    city: str = "Dublin,IE",
    per_page: int = 40,
    db: Session = Depends(get_db),
):
    access_token = get_latest_access_token(db, user_id)

    if not access_token:
        raise HTTPException(
            status_code=404,
            detail="No Strava token found for this user",
        )

    return recommend_training_today(
        access_token=access_token,
        city=city,
        per_page=per_page,
    )


@app.post("/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    access_token = get_latest_access_token(db, request.user_id)

    if not access_token:
        raise HTTPException(
            status_code=404,
            detail="No Strava token found for this user",
        )

    result = run_paceai_agent(
        user_message=request.message,
        access_token=access_token,
    )

    return result