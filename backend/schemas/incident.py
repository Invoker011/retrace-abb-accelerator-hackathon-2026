"""Incident and Timeline Event schemas."""
from typing import Any, Dict, Optional
from backend.schemas.base import BaseModel, Field

class Incident(BaseModel):
    id: str
    title: str
    plant_area: str = Field(..., alias="plantArea")
    severity: str  # Critical, High, Medium, Low
    status: str    # Under Investigation, Triaged, Resolved, Closed
    date: str
    started_at: str = Field(..., alias="startedAt")
    resolved_at: Optional[str] = Field(default=None, alias="resolvedAt")
    summary: str
    lead_investigator: str = Field(..., alias="leadInvestigator")
    unresolved_questions_count: int = Field(..., alias="unresolvedQuestionsCount")

    class Config:
        populate_by_name = True

class IncidentEvent(BaseModel):
    id: str
    incident_id: str = Field(..., alias="incidentId")
    timestamp: str
    display_time: str = Field(..., alias="displayTime")
    relative_seconds: int = Field(..., alias="relativeSeconds")
    asset_id: str = Field(..., alias="assetId")
    asset_name: str = Field(..., alias="assetName")
    event_type: str = Field(..., alias="eventType")
    title: str
    description: str
    evidence_id: str = Field(..., alias="evidenceId")
    evidence_ref: str = Field(..., alias="evidenceRef")
    severity: str
    telemetry_snapshot: Optional[Dict[str, Any]] = Field(default=None, alias="telemetrySnapshot")

    class Config:
        populate_by_name = True
