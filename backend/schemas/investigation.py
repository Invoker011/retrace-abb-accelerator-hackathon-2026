"""Investigation request and response schemas."""
from typing import Any, Dict, List, Optional
from backend.schemas.base import BaseModel, Field
from backend.schemas.finding import Finding, FindingClassification

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
