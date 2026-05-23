from sqlalchemy.orm import Session

from app.database.models import StravaToken


def get_latest_access_token(db: Session, user_id: int) -> str | None:
    token = (
        db.query(StravaToken)
        .filter(StravaToken.user_id == user_id)
        .order_by(StravaToken.created_at.desc())
        .first()
    )

    if not token:
        return None

    return token.access_token