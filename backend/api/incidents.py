"""Incident API endpoints."""
from typing import List
from fastapi import APIRouter, HTTPException, status
from backend.services.incident_service import incident_service
from backend.schemas.incident import Incident, IncidentEvent
from backend.schemas.asset import Asset, AssetRelationship
from backend.schemas.finding import Finding
from backend.schemas.evidence import Evidence
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
