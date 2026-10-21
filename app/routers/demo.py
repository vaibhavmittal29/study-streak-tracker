"""Demo mode endpoints: reset and status checks."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.clock import get_clock
from app.config import settings
from app.database import get_db
from app.services.demo_seeder import seed_demo_data

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/status")
def get_demo_status() -> dict:
    """Return whether the current server instance is operating in demo mode."""
    return {
        "demo_mode": settings.DEMO_MODE,
        "max_sessions": settings.DEMO_MAX_SESSIONS,
    }


@router.post("/reset")
def reset_demo_data(
    db: Session = Depends(get_db),
    today: date = Depends(get_clock),
) -> dict:
    """Wipe and re-seed deterministic demonstration study sessions.

    Available strictly when DEMO_MODE is enabled; returns 404 otherwise.
    """
    if not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo mode is disabled on this server instance",
        )

    count = seed_demo_data(db, today=today, reset=True)
    return {
        "status": "ok",
        "message": "Demo data reset successfully",
        "sessions_count": count,
    }
