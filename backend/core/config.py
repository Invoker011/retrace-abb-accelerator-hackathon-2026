"""Core configuration for RETRACE backend application."""
import os
from typing import List

class Settings:
    PROJECT_NAME: str = "RETRACE Multimodal Industrial Maintenance Intelligence API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Server Host & Port (PORT is supplied dynamically by Cloud Run, default 8000 for local dev)
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # CORS Configuration
    # Safe localhost development defaults - configurable via CORS_ORIGINS env variable
    DEFAULT_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    @classmethod
    def get_cors_origins(cls) -> List[str]:
        raw_origins = os.getenv("CORS_ORIGINS", "").strip()
        if raw_origins:
            parsed = [
                origin.strip().strip("'\"")
                for origin in raw_origins.split(",")
                if origin.strip().strip("'\"")
            ]
            return parsed if parsed else cls.DEFAULT_CORS_ORIGINS
        return cls.DEFAULT_CORS_ORIGINS

    CORS_ORIGINS: List[str] = get_cors_origins()

settings = Settings()
