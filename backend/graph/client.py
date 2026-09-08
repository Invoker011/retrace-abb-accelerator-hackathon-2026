"""Neo4j Client and Connection Management for RETRACE.

Provides safe driver initialization, session management, and connectivity health
probes without leaking credentials, URIs, usernames, or stack traces.
"""
import logging
from typing import Any, Optional
from contextlib import contextmanager

from backend.core.config import settings

logger = logging.getLogger(__name__)

try:
    import neo4j
    from neo4j import GraphDatabase, Driver
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False
    Driver = None  # type: ignore

_driver: Optional[Any] = None


def get_neo4j_driver() -> Optional[Any]:
    """Retrieve or lazily initialize the singleton Neo4j driver.

    Never logs credentials, usernames or raw URIs.
    """
    global _driver
    if _driver is not None:
        return _driver

    if not HAS_NEO4J:
        logger.info("[RETRACE] Neo4j Python driver not installed; graph layer will use fallback.")
        return None

    uri = settings.NEO4J_URI
    username = settings.NEO4J_USERNAME
    password = settings.NEO4J_PASSWORD

    if not uri or not username or not password:
        return None

    try:
        _driver = GraphDatabase.driver(
            uri,
            auth=(username, password),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_acquisition_timeout=10.0,
        )
        return _driver
    except Exception as e:
        # Safe log without credentials or URI
        logger.warning("[RETRACE] Failed to initialize Neo4j driver: %s", type(e).__name__)
        return None


def close_neo4j_driver() -> None:
    """Close active Neo4j driver connections during shutdown."""
    global _driver
    if _driver is not None:
        try:
            _driver.close()
        except Exception as e:
            logger.warning("[RETRACE] Error closing Neo4j driver: %s", type(e).__name__)
        finally:
            _driver = None


@contextmanager
def get_neo4j_session(database: Optional[str] = None):
    """Context manager for acquiring a Neo4j session safely."""
    driver = get_neo4j_driver()
    if driver is None:
        raise RuntimeError("Neo4j driver is not available or not configured.")

    target_db = database or settings.NEO4J_DATABASE or "neo4j"
    session = driver.session(database=target_db)
    try:
        yield session
    finally:
        session.close()


def check_neo4j_health() -> str:
    """Verifies Neo4j graph database connectivity without leaking credentials.

    Safe statuses returned:
      - 'connected': Driver connection verified successfully
      - 'not_configured': NEO4J_URI, NEO4J_USERNAME, or NEO4J_PASSWORD not configured
      - 'unavailable': Configured but connection attempt or driver verification failed
    """
    uri = settings.NEO4J_URI
    username = settings.NEO4J_USERNAME
    password = settings.NEO4J_PASSWORD

    if not uri or not username or not password:
        return "not_configured"

    if not HAS_NEO4J:
        return "unavailable"

    driver = get_neo4j_driver()
    if driver is None:
        return "unavailable"

    try:
        driver.verify_connectivity()
        return "connected"
    except Exception as e:
        logger.warning("[RETRACE] Neo4j health probe failed: %s", type(e).__name__)
        return "unavailable"
