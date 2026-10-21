"""FastAPI entry point for the Study Streak Tracker.

Configures application metadata, lifespan lifecycle (table creation),
and core health endpoints.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import (
    demo,
    export,
    goals,
    insights,
    sessions,
    stats,
    streaks,
)
from app.routers import settings as settings_router

# Configure clean structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("study_tracker")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Perform startup tasks: initialize database tables and auto-seed demo data if enabled."""
    Base.metadata.create_all(bind=engine)

    if settings.DEMO_MODE:
        from app.clock import get_today
        from app.database import SessionLocal
        from app.services.demo_seeder import seed_demo_data

        db = SessionLocal()
        try:
            seed_demo_data(db, today=get_today(settings.DEFAULT_TIMEZONE), reset=False)
        finally:
            db.close()

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
app.include_router(export.router)
app.include_router(insights.router)
app.include_router(demo.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Safely log uncaught internal exceptions without leaking stack traces."""
    logger.error("Uncaught exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"},
    )


# Static file serving & single-page application mount
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def serve_index() -> FileResponse:
    """Serve single-page frontend application dashboard."""
    return FileResponse(static_dir / "index.html")


@app.get("/api/health", summary="Health check endpoint")
def health_check() -> dict[str, str]:
    """Return application operational status."""
    return {"status": "ok"}
