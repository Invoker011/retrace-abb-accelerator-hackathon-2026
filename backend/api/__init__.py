"""API router configuration."""
from fastapi import APIRouter
from backend.api.incidents import router as incidents_router
from backend.api.evidence import router as evidence_router
from backend.api.investigation import router as investigation_router

api_router = APIRouter()
api_router.include_router(incidents_router)
api_router.include_router(evidence_router)
api_router.include_router(investigation_router)

__all__ = ["api_router"]
