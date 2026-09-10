"""Qdrant client and connection management for RETRACE.

Provides lazy initialization, HTTPS enforcement in production, safe health probes,
and idempotent collection provisioning without exposing secrets, credentials, or URLs.
"""
import logging
from typing import Any, Dict, Optional

from backend.core.config import settings

logger = logging.getLogger("retrace.vector")

try:
    import qdrant_client
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
    from qdrant_client.http.exceptions import UnexpectedResponse
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False
    QdrantClient = None  # type: ignore
    qmodels = None  # type: ignore
    UnexpectedResponse = Exception  # type: ignore

_client: Optional[Any] = None


def validate_qdrant_url(url: str, is_development: bool = False) -> None:
    """Validate connection URL security requirements."""
    if not url or not url.strip():
        raise ValueError("Qdrant URL must not be empty.")
    
    clean_url = url.strip().lower()
    is_localhost = clean_url.startswith("http://localhost") or clean_url.startswith("http://127.0.0.1")
    
    if clean_url.startswith("https://") or is_localhost:
        return
    
    if not is_development:
        raise ValueError("Production Qdrant connection must use HTTPS.")


def get_qdrant_client() -> Optional[Any]:
    """Retrieve or lazily initialize the singleton QdrantClient.

    Never logs credentials, API keys, or full secret URLs.
    """
    global _client
    if _client is not None:
        return _client

    if not HAS_QDRANT:
        logger.info("[RETRACE] qdrant-client not installed; vector layer will require in-memory or fallback provider.")
        return None

    url = settings.QDRANT_URL
    api_key = settings.QDRANT_API_KEY

    if not url:
        return None

    is_dev = (settings.ENVIRONMENT == "development")
    validate_qdrant_url(url, is_development=is_dev)

    try:
        _client = QdrantClient(
            url=url,
            api_key=api_key,
            timeout=10.0,
        )
        return _client
    except Exception as e:
        logger.warning("[RETRACE] Failed to initialize QdrantClient: %s", type(e).__name__)
        return None


def close_qdrant_client() -> None:
    """Close active Qdrant client connection during shutdown or testing."""
    global _client
    if _client is not None:
        try:
            if hasattr(_client, "close"):
                _client.close()
        except Exception as e:
            logger.warning("[RETRACE] Error closing QdrantClient: %s", type(e).__name__)
        finally:
            _client = None


def set_qdrant_client(client: Optional[Any]) -> None:
    """Inject a custom or mock QdrantClient for testing."""
    global _client
    _client = client


def check_qdrant_health() -> Dict[str, Any]:
    """Verify Qdrant connectivity without leaking credentials or mutating collections.

    Possible statuses:
      - connected: {"vector": "connected", "provider": "qdrant", "collection": "..."}
      - not_configured: {"vector": "not_configured"}
      - unavailable: {"vector": "unavailable"}
    """
    if not settings.QDRANT_URL:
        return {"vector": "not_configured"}

    if not HAS_QDRANT:
        return {"vector": "unavailable"}

    client = get_qdrant_client()
    if client is None:
        return {"vector": "unavailable"}

    try:
        # Read-only health probe: read collection list without mutating
        client.get_collections()
        return {
            "vector": "connected",
            "provider": "qdrant",
            "collection": settings.QDRANT_COLLECTION,
        }
    except Exception as e:
        logger.warning("[RETRACE] Qdrant health check failed: %s", type(e).__name__)
        return {"vector": "unavailable"}


def ensure_collection(
    client: Any,
    collection_name: Optional[str] = None,
    vector_size: Optional[int] = None,
    distance_str: str = "COSINE",
) -> bool:
    """Ensure the target Qdrant collection exists and has matching vector configuration.

    - If collection does not exist: create it with vector_size and COSINE distance.
    - If collection exists: verify vector_size and distance configuration.
    - If configuration does not match: raise ValueError without deleting existing data.
    - Provision keyword payload indexes for fast incident/asset filtering.

    Returns True if collection was newly created, False if existing collection was verified.
    """
    col_name = collection_name or settings.QDRANT_COLLECTION
    v_size = vector_size or settings.QDRANT_VECTOR_SIZE

    if client is None:
        raise RuntimeError("QdrantClient is not available to ensure collection.")

    if not client.collection_exists(col_name):
        if qmodels is not None:
            distance = qmodels.Distance.COSINE
            vectors_config = qmodels.VectorParams(size=v_size, distance=distance)
            keyword_schema = qmodels.PayloadSchemaType.KEYWORD
        else:
            vectors_config = {"size": v_size, "distance": "Cosine"}
            keyword_schema = "keyword"

        client.create_collection(
            collection_name=col_name,
            vectors_config=vectors_config,
        )
        logger.info("[RETRACE] Created Qdrant collection '%s' (size=%d, distance=COSINE)", col_name, v_size)

        # Create keyword payload indexes for high-frequency filters
        index_fields = [
            "managed_by",
            "incident_id",
            "evidence_id",
            "asset_id",
            "source_type",
            "modality",
        ]
        for field in index_fields:
            try:
                client.create_payload_index(
                    collection_name=col_name,
                    field_name=field,
                    field_schema=keyword_schema,
                )
            except Exception as e:
                logger.debug("[RETRACE] Index creation note for %s: %s", field, type(e).__name__)

        return True
    else:
        # Collection already exists: verify its configuration
        info = client.get_collection(col_name)
        vectors_config = getattr(info.config.params, "vectors", None)

        actual_size = None
        actual_distance = None

        if hasattr(vectors_config, "size"):
            actual_size = vectors_config.size
            actual_distance = vectors_config.distance
        elif isinstance(vectors_config, dict):
            first_param = next(iter(vectors_config.values()), None)
            if first_param is not None:
                actual_size = getattr(first_param, "size", None)
                actual_distance = getattr(first_param, "distance", None)

        if actual_size is not None and actual_size != v_size:
            raise ValueError(
                f"Qdrant collection '{col_name}' vector dimension mismatch: "
                f"expected {v_size}, but found existing collection with {actual_size}. "
                "Automatic deletion is prohibited to preserve industrial data integrity."
            )

        if actual_distance is not None:
            expected_dist_name = distance_str.lower()
            actual_dist_name = str(actual_distance).lower().split(".")[-1]
            if actual_dist_name != expected_dist_name:
                raise ValueError(
                    f"Qdrant collection '{col_name}' distance mismatch: "
                    f"expected {expected_dist_name}, but found existing collection with {actual_dist_name}."
                )

        logger.debug("[RETRACE] Verified existing Qdrant collection '%s' configuration", col_name)
        return False
