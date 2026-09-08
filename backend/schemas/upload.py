"""Schemas for uploaded industrial evidence artifacts."""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

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
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        populate_by_name = True

class EvidenceUploadResponse(BaseModel):
    status: str
    message: str
    evidence: UploadedEvidence
