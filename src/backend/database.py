"""
PanataanPH Database Configuration and Session Management.

Provides SQLite connection via SQLAlchemy 2.0, session factory,
FastAPI dependency, and table initialization.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator


# ---------------------------------------------------------------------------
# Database path configuration
# ---------------------------------------------------------------------------
# Default: data/panataanph.db relative to the project root.
# Override with the PANATAANPH_DB_PATH environment variable.
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # src/backend -> src -> project root
_DEFAULT_DB_DIR = _PROJECT_ROOT / "data"
_DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "panataanph.db"

DATABASE_PATH: str = os.getenv("PANATAANPH_DB_PATH", str(_DEFAULT_DB_PATH))
DATABASE_URL: str = f"sqlite:///{DATABASE_PATH}"


# ---------------------------------------------------------------------------
# SQLAlchemy Engine & Session
# ---------------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite with FastAPI
    echo=False,  # Set True for SQL query logging during development
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# ---------------------------------------------------------------------------
# FastAPI Dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session.

    Usage in a route:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Create all tables defined by ORM models.

    Call this once at application startup or from the init script.
    The data directory is created automatically if it does not exist.
    """
    # Ensure the directory for the SQLite file exists
    db_dir = Path(DATABASE_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    # Import models so they register with Base.metadata
    from backend import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized at: {DATABASE_PATH}")
