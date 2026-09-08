"""Incident API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from backend.services.incident_service import incident_service
from backend.services.upload_service import ingestion_service, IngestionError
from backend.schemas.incident import Incident, IncidentEvent
from backend.schemas.asset import Asset, AssetRelationship
from backend.schemas.finding import Finding
from backend.schemas.evidence import Evidence
from backend.schemas.upload import UploadedEvidence
from backend.schemas.prevention import PreventionScenario
from backend.schemas.context import IncidentContextResponse

router = APIRouter(prefix="/incidents", tags=["Incidents"])

@router.get("", response_model=List[Incident], summary="List all incidents")
def list_incidents() -> List[Incident]:
    return incident_service.get_all_incidents()

@router.get("/{incident_id}", response_model=Incident, summary="Get incident details")
def get_incident(incident_id: str) -> Incident:
    incident = incident_service.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return incident

@router.get("/{incident_id}/events", response_model=List[IncidentEvent], summary="Get incident timeline events")
def get_incident_events(incident_id: str) -> List[IncidentEvent]:
    incident = incident_service.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return incident_service.get_incident_events(incident_id)

@router.get("/{incident_id}/assets", response_model=List[Asset], summary="Get assets involved in the incident")
def get_incident_assets(incident_id: str) -> List[Asset]:
    incident = incident_service.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return incident_service.get_incident_assets(incident_id)

@router.get("/{incident_id}/relationships", response_model=List[AssetRelationship], summary="Get asset relationships")
def get_incident_relationships(incident_id: str) -> List[AssetRelationship]:
    incident = incident_service.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return incident_service.get_asset_relationships(incident_id)

@router.get("/{incident_id}/findings", response_model=List[Finding], summary="Get incident findings")
def get_incident_findings(incident_id: str) -> List[Finding]:
    incident = incident_service.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return incident_service.get_incident_findings(incident_id)

@router.get("/{incident_id}/evidence", response_model=List[Evidence], summary="Get evidence connected to incident")
def get_incident_evidence(incident_id: str) -> List[Evidence]:
    incident = incident_service.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return incident_service.get_incident_evidence(incident_id)

@router.get("/{incident_id}/context", response_model=IncidentContextResponse, summary="Get combined incident context")
def get_incident_context(incident_id: str) -> IncidentContextResponse:
    context = incident_service.get_incident_context(incident_id)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return context

@router.get("/{incident_id}/prevention", response_model=PreventionScenario, summary="Get prevention / counterfactual scenario")
def get_incident_prevention(incident_id: str) -> PreventionScenario:
    incident = incident_service.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    scenario = incident_service.get_prevention_scenario(incident_id)
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prevention scenario not available for incident '{incident_id}'.",
        )
    return scenario

@router.post(
    "/{incident_id}/evidence/upload",
    response_model=UploadedEvidence,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and securely register new industrial evidence for an incident",
)
async def upload_incident_evidence(
    incident_id: str,
    file: UploadFile = File(...),
    source_type: str = Form(...),
    asset_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
) -> UploadedEvidence:
    incident = incident_service.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )

    try:
        content = await file.read()
        uploaded_record = ingestion_service.upload_evidence(
            incident_id=incident_id,
            original_filename=file.filename or "unknown_file",
            content_type=file.content_type,
            file_bytes=content,
            source_type=source_type,
            asset_id=asset_id,
            description=description,
        )
        return uploaded_record
    except IngestionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and store evidence: {str(e)}",
        )

@router.get(
    "/{incident_id}/evidence/uploads",
    response_model=List[UploadedEvidence],
    summary="List newly uploaded evidence artifacts registered for an incident",
)
def list_incident_uploads(incident_id: str) -> List[UploadedEvidence]:
    incident = incident_service.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return ingestion_service.get_uploads_for_incident(incident_id)

