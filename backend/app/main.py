"""Main FastAPI application entry point for RETRACE.
Multimodal Industrial Maintenance Intelligence & Incident Investigation.
"""

import sys
from pathlib import Path

# Add backend directory and parent directory to sys.path to allow modular imports
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
_project_root = _backend_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Multimodal Industrial Maintenance Intelligence and Incident Investigation API for RETRACE.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
# Configured via CORS_ORIGINS environment variable with safe localhost development defaults
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Global Exception Handler to avoid exposing stack traces or internals
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # In production/API responses, do not leak raw stack traces
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred in RETRACE intelligence service."},
    )

# Root service status
@app.get("/", tags=["General"])
def root():
    return {
        "service": "RETRACE Industrial Intelligence API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
    }

# Health Check Endpoint
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "RETRACE API",
    }

# Mount the modular API router under /api
app.include_router(api_router, prefix=settings.API_PREFIX)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development"),
    )
