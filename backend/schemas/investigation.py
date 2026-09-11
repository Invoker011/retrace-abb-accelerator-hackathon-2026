"""Investigation request and response schemas."""
from typing import Any, Dict, List, Optional
from backend.schemas.base import BaseModel, Field
from backend.schemas.finding import Finding, FindingClassification

try:
    from pydantic import field_validator
    HAS_FIELD_VALIDATOR = True
except ImportError:
    HAS_FIELD_VALIDATOR = False


class InvestigationRequest(BaseModel):
    """Request payload for grounded investigation reasoning."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Investigator or technician troubleshooting question",
    )
    top_k: int = Field(
        default=8,
        ge=1,
        le=20,
        description="Number of fused evidence chunks to retrieve for reasoning (1-20)",
    )
    asset_id: Optional[str] = Field(
        default=None,
        description="Optional asset identifier filter",
    )
    source_type: Optional[str] = Field(
        default=None,
        description="Optional industrial source type filter",
    )

    def __init__(self, **kwargs):
        if "query" in kwargs and isinstance(kwargs["query"], str):
            kwargs["query"] = kwargs["query"].strip()
            if not kwargs["query"]:
                raise ValueError("Investigation query must not be empty or whitespace only.")
            if len(kwargs["query"]) > 1000:
                raise ValueError("Investigation query exceeds maximum length of 1000 characters.")
        if "top_k" in kwargs and kwargs["top_k"] is not None:
            try:
                k = int(kwargs["top_k"])
                kwargs["top_k"] = min(max(1, k), 20)
            except (ValueError, TypeError):
                kwargs["top_k"] = 8
        super().__init__(**kwargs)

    if HAS_FIELD_VALIDATOR:
        @field_validator("query")
        @classmethod
        def validate_query(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("Investigation query must not be empty or whitespace only.")
            clean = v.strip()
            if len(clean) > 1000:
                raise ValueError("Investigation query exceeds maximum length of 1000 characters.")
            return clean

        @field_validator("top_k")
        @classmethod
        def validate_top_k(cls, v: int) -> int:
            if v < 1 or v > 20:
                raise ValueError("top_k must be between 1 and 20.")
            return v


class InvestigationFinding(BaseModel):
    """Classified and grounded finding from reasoning over retrieved context."""
    classification: FindingClassification = Field(
        ...,
        description="Finding classification: OBSERVED, CORRELATED, HYPOTHESIS, or UNKNOWN",
    )
    statement: str = Field(
        ...,
        description="Factual, correlated, or hypothetical finding statement",
    )
    basis: str = Field(
        ...,
        description="Concise evidence-grounded explanation (no private chain-of-thought)",
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


class RecommendedCheck(BaseModel):
    """Advisory diagnostic inspection step. Never an autonomous control or actuation command."""
    check: str = Field(
        ...,
        description="Recommended diagnostic inspection or verification check",
    )
    reason: str = Field(
        ...,
        description="Diagnostic justification for recommending this inspection",
    )
    related_asset_ids: List[str] = Field(
        default_factory=list,
        description="Associated asset identifiers",
    )


class EvidenceCitation(BaseModel):
    """Compact citation of evidence source utilized during reasoning."""
    evidence_id: str = Field(..., description="Parent evidence identifier (e.g. EVD-001)")
    chunk_id: Optional[str] = Field(default=None, description="Specific chunk identifier")
    asset_id: Optional[str] = Field(default=None, description="Associated asset identifier")
    filename: str = Field(..., description="Original evidence filename")
    source_type: str = Field(..., description="Industrial evidence source category")
    timestamp: Optional[str] = Field(default=None, description="Timestamp of the evidence record")
    original_reference: Optional[str] = Field(default=None, description="Original source or section reference")


# Alias for EvidenceCitation
InvestigationSource = EvidenceCitation


class InvestigationResponse(BaseModel):
    """Complete grounded investigation response payload."""
    incident_id: str = Field(..., description="Target incident identifier")
    query: str = Field(..., description="Original investigation question")
    summary: str = Field(..., description="Synthesized grounded investigation assessment")
    findings: List[InvestigationFinding] = Field(
        default_factory=list,
        description="Classified grounded findings",
    )
    unknowns: List[str] = Field(
        default_factory=list,
        description="Unknowns and unresolved evidence gaps",
    )
    recommended_checks: List[RecommendedCheck] = Field(
        default_factory=list,
        description="Advisory diagnostic checks",
    )
    sources_used: List[EvidenceCitation] = Field(
        default_factory=list,
        description="Evidence sources included in reasoning context",
    )


class InvestigationQueryRequest(BaseModel):
    incident_id: str = Field(..., alias="incidentId")
    question: str

    class Config:
        populate_by_name = True


class InvestigationQueryResponse(BaseModel):
    answer: str
    findings: List[Finding] = Field(default_factory=list)
    supporting_evidence: List[Dict[str, Any]] = Field(default_factory=list, alias="supportingEvidence")
    classification: FindingClassification
    unresolved_questions: List[str] = Field(default_factory=list, alias="unresolvedQuestions")
    suggested_follow_ups: Optional[List[str]] = Field(default=None, alias="suggestedFollowUps")

    class Config:
        populate_by_name = True
        use_enum_values = True

