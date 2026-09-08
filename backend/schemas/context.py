"""Combined Incident Context schema."""
from typing import List
from pydantic import BaseModel
from backend.schemas.incident import Incident, IncidentEvent
from backend.schemas.asset import Asset, AssetRelationship
from backend.schemas.evidence import Evidence
from backend.schemas.finding import Finding

class IncidentContextResponse(BaseModel):
    incident: Incident
    events: List[IncidentEvent]
    assets: List[Asset]
    relationships: List[AssetRelationship]
    evidence: List[Evidence]
    findings: List[Finding]

    class Config:
        populate_by_name = True
