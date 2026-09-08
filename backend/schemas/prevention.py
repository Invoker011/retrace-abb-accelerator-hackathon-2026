"""Prevention and Counterfactual Scenario schemas."""
from typing import List, Optional
from backend.schemas.base import BaseModel, Field

class PreventionNode(BaseModel):
    step: int
    title: str
    asset_id: Optional[str] = Field(default=None, alias="assetId")
    asset_name: Optional[str] = Field(default=None, alias="assetName")
    time_offset: str = Field(..., alias="timeOffset")
    status: str  # critical_path, intervention_point, mitigation_outcome, normal
    description: str
    safeguard_type: Optional[str] = Field(default=None, alias="safeguardType")

    class Config:
        populate_by_name = True

class PreventionSafeguard(BaseModel):
    title: str
    category: str
    status: str
    recommendation: str

class PreventionScenario(BaseModel):
    incident_id: str = Field(..., alias="incidentId")
    actual_path: List[PreventionNode] = Field(..., alias="actualPath")
    possible_intervention_path: List[PreventionNode] = Field(..., alias="interventionPath")
    disclaimer: str
    safeguards: List[PreventionSafeguard] = Field(default_factory=list)

    class Config:
        populate_by_name = True
