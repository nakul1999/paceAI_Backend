from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    strava_athlete_id = Column(String, unique=True, index=True)
    firstname = Column(String)
    lastname = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    tokens = relationship("StravaToken", back_populates="user")
    activities = relationship("Activity", back_populates="user")


class StravaToken(Base):
    __tablename__ = "strava_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    access_token = Column(Text)
    refresh_token = Column(Text)
    expires_at = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="tokens")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    strava_id = Column(String, unique=True, index=True)
    name = Column(String)
    date = Column(DateTime)

    distance_km = Column(Float)
    duration_minutes = Column(Float)
    pace_min_per_km = Column(Float)
    elevation_gain_m = Column(Float)
    average_heartrate = Column(Float)
    max_heartrate = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="activities")


class ACWRResult(Base):
    __tablename__ = "acwr_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    current_acwr = Column(Float)
    acute_load_7d = Column(Float)
    chronic_load_28d_avg = Column(Float)
    status = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    role = Column(String)
    content = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)