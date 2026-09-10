"""Core configuration for RETRACE backend application."""
import os
from typing import List, Optional

DEFAULT_CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

def parse_cors_origins() -> List[str]:
    """Parse CORS origins from CORS_ORIGINS environment variable.
    Splits comma-separated origins, trims whitespace/quotes, and filters empty entries.
    Falls back to safe localhost development defaults if unset or empty.
    """
    raw_origins = os.getenv("CORS_ORIGINS", "").strip()
    if raw_origins:
        parsed = [
            origin.strip().strip("'\"")
            for origin in raw_origins.split(",")
            if origin.strip().strip("'\"")
        ]
        if parsed:
            return parsed
    return DEFAULT_CORS_ORIGINS

class Settings:
    PROJECT_NAME: str = "RETRACE Multimodal Industrial Maintenance Intelligence API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Server Host & Port (PORT is supplied dynamically by Cloud Run, default 8000 for local dev)
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # CORS Configuration
    CORS_ORIGINS: List[str] = parse_cors_origins()

    # PostgreSQL Database URL (read only from server-side environment)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # Neo4j Graph Database (Server-side only, never exposed to client)
    NEO4J_URI: Optional[str] = os.getenv("NEO4J_URI")
    NEO4J_USERNAME: Optional[str] = os.getenv("NEO4J_USERNAME")
    NEO4J_PASSWORD: Optional[str] = os.getenv("NEO4J_PASSWORD")
    NEO4J_DATABASE: Optional[str] = (
        os.getenv("NEO4J_DATABASE", "").strip() or None
    )

    # Qdrant Vector Database (Server-side only, optional at config parse time)
    QDRANT_URL: Optional[str] = (os.getenv("QDRANT_URL", "").strip() or None)
    QDRANT_API_KEY: Optional[str] = (os.getenv("QDRANT_API_KEY", "").strip() or None)
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "retrace_evidence_v1")
    QDRANT_VECTOR_SIZE: int = int(os.getenv("QDRANT_VECTOR_SIZE", "768"))

    # Vertex AI Multimodal Embedding Settings
    GOOGLE_CLOUD_PROJECT: str = (
        os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        or os.getenv("GCP_PROJECT", "").strip()
        or "retrace-abb-2026"
    )
    GOOGLE_CLOUD_LOCATION: str = (
        os.getenv("GOOGLE_CLOUD_LOCATION", "").strip()
        or os.getenv("GOOGLE_CLOUD_REGION", "").strip()
        or "us-central1"
    )
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "").strip() or "gemini-embedding-001"
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))

settings = Settings()
