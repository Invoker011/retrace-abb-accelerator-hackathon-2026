"""Investigation API endpoints."""
from fastapi import APIRouter, HTTPException, status
from backend.services.incident_service import incident_service
from backend.services.investigation_service import investigation_service
from backend.schemas.investigation import InvestigationQueryRequest, InvestigationQueryResponse

router = APIRouter(prefix="/investigation", tags=["Investigation"])

@router.post("/query", response_model=InvestigationQueryResponse, summary="Query technician troubleshooting assistant")
def query_investigation(req: InvestigationQueryRequest) -> InvestigationQueryResponse:
    # Verify incident exists
    incident = incident_service.get_incident_by_id(req.incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{req.incident_id}' not found.",
        )
    return investigation_service.query(req.incident_id, req.question)
