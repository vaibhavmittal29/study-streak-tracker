"""Database setup and session lifecycle management.

Configures SQLAlchemy engine, session maker, declarative base,
and FastAPI dependency for database sessions.
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

# Ensure data directory exists if a local SQLite file is configured
if settings.DATABASE_URL.startswith("sqlite:///./"):
    relative_path = settings.DATABASE_URL.replace("sqlite:///./", "")
    db_file_path = Path(relative_path)
    db_file_path.parent.mkdir(parents=True, exist_ok=True)

# SQLite requires check_same_thread=False when accessed by FastAPI threads
connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency providing a transactional database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
