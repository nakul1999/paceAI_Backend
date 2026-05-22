from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse
from app.tools.strava import get_recent_activities
from app.tools.acwr import calculate_acwr_from_activities
from app.tools.weather import get_current_weather
from app.tools.recommendation import recommend_training_today
from app.agents.paceai_agent import run_paceai_agent
from app.services.strava_oauth import (
    get_strava_auth_url,
    exchange_code_for_token,
)
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from app.database.db import Base, engine
from app.database import models
from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.database.models import User, StravaToken



class ChatRequest(BaseModel):
    message: str
    access_token: str

app = FastAPI(title="PaceAI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)



@app.get("/")
def root():
    return {"message": "PaceAI backend is running"}


@app.get("/auth/strava/login")
def strava_login():
    return RedirectResponse(get_strava_auth_url())


@app.get("/auth/strava/callback")
def strava_callback(code: str):

    token_data = exchange_code_for_token(code)

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_at = token_data.get("expires_at")

    athlete = token_data.get("athlete", {})

    db: Session = SessionLocal()

    try:
        existing_user = (
            db.query(User)
            .filter(
                User.strava_athlete_id == str(athlete["id"])
            )
            .first()
        )

        if not existing_user:
            user = User(
                strava_athlete_id=str(athlete["id"]),
                firstname=athlete.get("firstname"),
                lastname=athlete.get("lastname"),
            )

            db.add(user)
            db.commit()
            db.refresh(user)

        else:
            user = existing_user

        token = StravaToken(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        db.add(token)
        db.commit()
        frontend_url = (
            "http://localhost:3000/auth/callback"
            f"?user_id={user.id}"
        )
        return RedirectResponse(frontend_url)
    finally:
        db.close()

@app.get("/activities")
def activities(
    access_token: str,
    per_page: int = 40,
):
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
    access_token: str,
    per_page: int = 40
):
    activities = get_recent_activities(
        access_token=access_token,
        per_page=per_page
    )
    result = calculate_acwr_from_activities(
        activities
    )
    return result

@app.get("/weather")
def weather(city: str = "Dublin,IE"):
    return get_current_weather(city=city)

@app.get("/recommendation/today")
def today_recommendation(
    access_token: str,
    city: str = "Dublin,IE",
    per_page: int = 40,
):
    return recommend_training_today(
        access_token=access_token,
        city=city,
        per_page=per_page,
    )


@app.post("/chat")
def chat(request: ChatRequest):

    result = run_paceai_agent(
        user_message=request.message,
        access_token=request.access_token,
    )

    return result