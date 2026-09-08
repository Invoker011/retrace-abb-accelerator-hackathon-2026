"""Evidence API endpoints."""
from fastapi import APIRouter, HTTPException, status
from backend.services.evidence_service import evidence_service
from backend.schemas.evidence import Evidence

router = APIRouter(prefix="/evidence", tags=["Evidence"])

@router.get("/{evidence_id}", response_model=Evidence, summary="Get full evidence provenance record")
def get_evidence(evidence_id: str) -> Evidence:
    item = evidence_service.get_evidence_by_id(evidence_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence artifact '{evidence_id}' not found.",
        )
    return item
