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


# ============================================================================
# RETRACE Grounded Potential Prevention Paths Schemas
# ============================================================================

class PreventionPathsRequest(BaseModel):
    """Request payload for counterfactual prevention-paths investigation."""
    query: Optional[str] = Field(
        default="What could potentially have prevented or mitigated this incident?",
        description="Exploratory counterfactual question or prevention focus",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Number of candidate context chunks to retrieve (1-20)",
    )


class PreventionVerificationCheck(BaseModel):
    """Advisory human engineering review or verification check."""
    check: str = Field(..., description="Advisory human engineering review or check")
    purpose: str = Field(..., description="Purpose or intent of the verification check")


class PotentialPreventionPath(BaseModel):
    """Counterfactual opportunity that could potentially have mitigated the incident."""
    path_id: str = Field(..., description="Unique prevention path identifier (e.g. PP-001)")
    title: str = Field(..., description="Descriptive title of potential prevention path")
    hypothetical_intervention: str = Field(
        ...,
        description="Conditional, non-causal hypothetical intervention description",
    )
    potential_effect: str = Field(
        ...,
        description="Conditional description of potential effect or mitigation",
    )
    evidence_basis: str = Field(
        ...,
        description="Observed factual evidence basis grounding this path",
    )
    evidence_ids: List[str] = Field(
        default_factory=list,
        description="Directly supporting evidence IDs from retrieved context",
    )
    event_ids: List[str] = Field(
        default_factory=list,
        description="Directly supporting timeline event IDs from retrieved context",
    )
    asset_ids: List[str] = Field(
        default_factory=list,
        description="Associated asset identifiers from retrieved context",
    )
    uncertainties: List[str] = Field(
        default_factory=list,
        description="Mandatory uncertainties and unconfirmed factors",
    )
    verification_checks: List[PreventionVerificationCheck] = Field(
        default_factory=list,
        description="Advisory engineering verification checks",
    )


class PreventionEvidenceCitation(BaseModel):
    """Compact citation of evidence source utilized during prevention path reasoning."""
    evidence_id: str = Field(..., description="Parent evidence identifier (e.g. EVD-001)")
    chunk_id: Optional[str] = Field(default=None, description="Specific chunk identifier")
    asset_id: Optional[str] = Field(default=None, description="Associated asset identifier")
    filename: str = Field(..., description="Original evidence filename")
    source_type: str = Field(..., description="Industrial evidence source category")
    timestamp: Optional[str] = Field(default=None, description="Timestamp of the evidence record")
    original_reference: Optional[str] = Field(default=None, description="Original source or section reference")


class PreventionPathsResponse(BaseModel):
    """Complete prevention paths response payload."""
    incident_id: str = Field(..., description="Target incident identifier")
    summary: str = Field(..., description="Synthesis of potential prevention opportunities")
    paths: List[PotentialPreventionPath] = Field(
        default_factory=list,
        description="Evidence-grounded potential prevention paths",
    )
    unknowns: List[str] = Field(
        default_factory=list,
        description="Information gaps and unconfirmed conditions",
    )
    sources_used: List[PreventionEvidenceCitation] = Field(
        default_factory=list,
        description="Retrieved evidence sources utilized",
    )
    disclaimer: str = Field(
        ...,
        description="Mandatory counterfactual advisory disclaimer",
    )
