"""Evidence schemas and multimodal source classifications."""
from typing import Any, Dict, List, Optional
from backend.schemas.base import BaseModel, Field

class Evidence(BaseModel):
    id: str
    source: str
    source_type: str = Field(..., alias="sourceType")
    filename: str
    original_timestamp: str = Field(..., alias="timestamp")
    normalized_timestamp: str = Field(..., alias="normalizedTimestamp")
    asset_id: str = Field(..., alias="assetId")
    extracted_content: str = Field(..., alias="extractedEvent")
    confidence: float
    original_reference: str = Field(..., alias="originalEvidenceRef")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Extended frontend convenience fields
    asset_name: Optional[str] = Field(default=None, alias="assetName")
    file_size: Optional[str] = Field(default=None, alias="fileSize")
    format: Optional[str] = None
    preview_rows: Optional[List[Dict[str, Any]]] = Field(default=None, alias="previewRows")
    raw_content: Optional[str] = Field(default=None, alias="rawContent")

    class Config:
        populate_by_name = True
