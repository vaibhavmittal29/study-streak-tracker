"""FastAPI entry point for the Study Streak Tracker.

Configures application metadata, lifespan lifecycle (table creation),
and core health endpoints.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import export, goals, sessions, stats, streaks
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
app.include_router(export.router)

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
