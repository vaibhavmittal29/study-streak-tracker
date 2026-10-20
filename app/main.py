"""FastAPI entry point for the Study Streak Tracker.

Configures application metadata, lifespan lifecycle, API routers,
and health endpoints.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Study Streak Tracker",
    description=(
        "A single-user study streak and habit tracker with automated streak computation, "
        "weekly subject statistics, and AI/ML-driven consistency forecasting."
    ),
    version="1.0.0",
)


@app.get("/api/health", summary="Health check endpoint")
def health_check() -> dict[str, str]:
    """Return application operational status."""
    return {"status": "ok"}
