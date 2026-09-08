"""Database engine and session management for RETRACE PostgreSQL."""
import os
import logging
from contextlib import contextmanager
from typing import Generator, Optional

from backend.core.config import settings

logger = logging.getLogger("retrace.database")

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    Session = Any = object  # type: ignore

_engine = None
_SessionLocal = None


def normalize_database_url(raw_url: Optional[str]) -> Optional[str]:
    """Normalizes database URL for SQLAlchemy 2.x and psycopg.
    Converts legacy postgres:// to postgresql+psycopg:// or postgresql://.
    Does not log or expose the connection string.
    """
    if not raw_url:
        return None
    url = raw_url.strip()
    if not url:
        return None
    # Replace legacy Heroku/GCP postgres:// prefix with postgresql+psycopg://
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def get_engine():
    """Initializes and returns the global SQLAlchemy engine if DATABASE_URL is configured."""
    global _engine, _SessionLocal
    if not HAS_SQLALCHEMY:
        return None

    if _engine is not None:
        return _engine

    raw_url = settings.DATABASE_URL or os.getenv("DATABASE_URL")
    normalized_url = normalize_database_url(raw_url)

    if not normalized_url:
        return None

    try:
        # Configure connection pool with safe recycling and timeout limits
        _engine = create_engine(
            normalized_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
            connect_args={"connect_timeout": 5} if "sqlite" not in normalized_url else {},
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        return _engine
    except Exception as e:
        # Never log raw connection string or passwords
        logger.error("[RETRACE] Failed to initialize database engine: %s", type(e).__name__)
        return None


def get_session_factory():
    """Returns SessionLocal factory if engine is available."""
    global _SessionLocal
    if _SessionLocal is None:
        get_engine()
    return _SessionLocal


@contextmanager
def get_db_session() -> Generator[Optional[Any], None, None]:
    """Context manager for acquiring and safely closing a database session.
    Commits on clean exit, rolls back on exception.
    """
    factory = get_session_factory()
    if factory is None:
        yield None
        return

    session = factory()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error("[RETRACE] Database session rollback due to error: %s", type(e).__name__)
        raise
    finally:
        session.close()


def check_database_health() -> str:
    """Verifies database connectivity without leaking credentials, hostnames or connection strings.
    Safe statuses returned:
      - 'connected': Active DB connection succeeded with SELECT 1
      - 'not_configured': DATABASE_URL is not configured
      - 'unreachable': DATABASE_URL is configured but connection cannot be established
    """
    raw_url = settings.DATABASE_URL or os.getenv("DATABASE_URL")
    if not raw_url:
        return "not_configured"

    if not HAS_SQLALCHEMY:
        return "unreachable"

    engine = get_engine()
    if engine is None:
        return "unreachable"

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "connected"
    except Exception as e:
        # Safe log without connection string or credentials
        logger.warning("[RETRACE] Database health probe failed: %s", type(e).__name__)
        return "unreachable"
