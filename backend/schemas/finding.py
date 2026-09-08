"""Finding schemas and classification definitions."""
from enum import Enum
from typing import List, Optional
from backend.schemas.base import BaseModel, Field

class FindingClassification(str, Enum):
    OBSERVED = "OBSERVED"
    CORRELATED = "CORRELATED"
    HYPOTHESIS = "HYPOTHESIS"
    UNKNOWN = "UNKNOWN"

class Finding(BaseModel):
    id: str
    incident_id: str = Field(..., alias="incidentId")
    category: FindingClassification
    statement: str
    supporting_evidence_ids: List[str] = Field(default_factory=list, alias="supportingEvidenceIds")
    related_asset_ids: List[str] = Field(default_factory=list, alias="relatedAssetIds")
    confidence_score: Optional[float] = Field(default=None, alias="confidenceScore")
    notes: Optional[str] = None

    class Config:
        populate_by_name = True
        use_enum_values = True
