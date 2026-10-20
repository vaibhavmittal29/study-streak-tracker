"""FastAPI entry point for the Study Streak Tracker.

Configures application metadata, lifespan lifecycle (table creation),
and core health endpoints.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import goals, sessions, stats, streaks
from app.routers import settings as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Perform startup tasks: initialize database tables."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Study Streak Tracker",
    description=(
        "A single-user study streak and habit tracker with automated streak computation, "
        "weekly subject statistics, and AI/ML-driven consistency forecasting."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(sessions.router)
app.include_router(streaks.router)
app.include_router(stats.router)
app.include_router(settings_router.router)
app.include_router(goals.router)


@app.get("/api/health", summary="Health check endpoint")
def health_check() -> dict[str, str]:
    """Return application operational status."""
    return {"status": "ok"}
