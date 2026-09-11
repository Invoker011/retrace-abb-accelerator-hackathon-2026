"""Schemas for uploaded industrial evidence artifacts."""
from typing import Any, Dict, Optional
from backend.schemas.base import BaseModel, Field

class UploadedEvidence(BaseModel):
    evidence_id: str = Field(..., alias="evidenceId")
    incident_id: str = Field(..., alias="incidentId")
    source_type: str = Field(..., alias="sourceType")
    original_filename: str = Field(..., alias="originalFilename")
    stored_filename: str = Field(..., alias="storedFilename")
    content_type: str = Field(..., alias="contentType")
    file_size: int = Field(..., alias="fileSize")
    asset_id: Optional[str] = Field(default=None, alias="assetId")
    description: Optional[str] = Field(default=None)
    storage_uri: str = Field(..., alias="storageUri")
    uploaded_at: str = Field(..., alias="uploadedAt")
    processing_status: str = Field(default="UPLOADED", alias="processingStatus")
    sha256_hash: str = Field(..., alias="sha256Hash")
    retrieval_eligible: bool = Field(default=True, alias="retrievalEligible")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    def __init__(self, **kwargs):
        if "retrievalEligible" in kwargs:
            kwargs["retrieval_eligible"] = kwargs["retrievalEligible"]
        elif "retrieval_eligible" not in kwargs:
            meta = kwargs.get("metadata") or {}
            if isinstance(meta, dict) and meta.get("retrieval_eligible") is False:
                kwargs["retrieval_eligible"] = False
            elif isinstance(meta, dict) and meta.get("use_type") in ("test", "verification"):
                kwargs["retrieval_eligible"] = False
            else:
                kwargs["retrieval_eligible"] = True
        super().__init__(**kwargs)

    class Config:
        populate_by_name = True

class EvidenceUploadResponse(BaseModel):
    status: str
    message: str
    evidence: UploadedEvidence
