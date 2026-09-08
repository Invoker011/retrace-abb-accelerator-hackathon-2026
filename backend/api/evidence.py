"""Evidence API endpoints."""
from fastapi import APIRouter, HTTPException, status
from backend.services.evidence_service import evidence_service
from backend.services.upload_service import ingestion_service
from backend.schemas.evidence import Evidence
from backend.schemas.upload import UploadedEvidence

router = APIRouter(prefix="/evidence", tags=["Evidence"])

@router.get("/uploads/{evidence_id}", response_model=UploadedEvidence, summary="Get uploaded evidence metadata")
def get_uploaded_evidence(evidence_id: str) -> UploadedEvidence:
    upload = ingestion_service.get_upload_by_id(evidence_id)
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Uploaded evidence artifact '{evidence_id}' not found.",
        )
    return upload

@router.delete("/uploads/{evidence_id}", summary="Delete uploaded evidence artifact and file")
def delete_uploaded_evidence(evidence_id: str):
    deleted = ingestion_service.delete_upload(evidence_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Uploaded evidence artifact '{evidence_id}' not found or already deleted.",
        )
    return {
        "status": "deleted",
        "evidence_id": evidence_id,
        "message": "Uploaded evidence record and underlying storage object removed successfully.",
    }

@router.get("/{evidence_id}", response_model=Evidence, summary="Get full evidence provenance record")
def get_evidence(evidence_id: str) -> Evidence:
    item = evidence_service.get_evidence_by_id(evidence_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence artifact '{evidence_id}' not found.",
        )
    return item

