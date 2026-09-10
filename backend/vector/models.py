"""Vector data models and API schemas for RETRACE Qdrant retrieval layer."""
import uuid
from typing import Any, Dict, List, Optional
from backend.schemas.base import BaseModel, Field


def generate_deterministic_point_id(incident_id: str, evidence_id: str, chunk_index: int) -> str:
    """Generate deterministic UUID5 point ID for Qdrant points.

    Guarantees that repeated vector sync updates the identical point
    rather than introducing duplicates.
    """
    name = f"retrace:{incident_id}:{evidence_id}:{chunk_index}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, name))


class EvidenceChunk(BaseModel):
    """Internal model representing a discrete factual evidence chunk in Qdrant."""
    point_id: str = Field(..., description="Deterministic UUID string identifier for Qdrant point")
    incident_id: str
    evidence_id: str
    chunk_id: str
    chunk_index: int
    asset_id: Optional[str] = None
    source_type: str
    filename: str
    content_type: str
    modality: str  # e.g., 'text', 'tabular', 'document', 'log'
    text: str
    storage_uri: str
    sha256_hash: str
    provenance: Dict[str, Any] = Field(default_factory=dict)
    managed_by: str = Field(default="retrace", description="Namespace marker for scoped deletions")
    page_number: Optional[int] = None
    row_start: Optional[int] = None
    row_end: Optional[int] = None
    timestamp: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        """Convert chunk into a clean Qdrant payload dictionary."""
        payload: Dict[str, Any] = {
            "managed_by": self.managed_by,
            "incident_id": self.incident_id,
            "evidence_id": self.evidence_id,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "asset_id": self.asset_id,
            "source_type": self.source_type,
            "filename": self.filename,
            "content_type": self.content_type,
            "modality": self.modality,
            "text": self.text,
            "storage_uri": self.storage_uri,
            "sha256_hash": self.sha256_hash,
            "provenance": self.provenance,
        }
        if self.page_number is not None:
            payload["page_number"] = self.page_number
        if self.row_start is not None:
            payload["row_start"] = self.row_start
        if self.row_end is not None:
            payload["row_end"] = self.row_end
        if self.timestamp is not None:
            payload["timestamp"] = self.timestamp
        return payload

    @classmethod
    def from_payload(cls, payload: Dict[str, Any], point_id: Optional[str] = None) -> "EvidenceChunk":
        """Instantiate EvidenceChunk from a Qdrant payload."""
        resolved_point_id = point_id or payload.get("point_id") or generate_deterministic_point_id(
            payload.get("incident_id", ""),
            payload.get("evidence_id", ""),
            payload.get("chunk_index", 0),
        )
        return cls(
            point_id=str(resolved_point_id),
            incident_id=payload.get("incident_id", ""),
            evidence_id=payload.get("evidence_id", ""),
            chunk_id=payload.get("chunk_id", ""),
            chunk_index=int(payload.get("chunk_index", 0)),
            asset_id=payload.get("asset_id"),
            source_type=payload.get("source_type", ""),
            filename=payload.get("filename", ""),
            content_type=payload.get("content_type", "text/plain"),
            modality=payload.get("modality", "text"),
            text=payload.get("text", ""),
            storage_uri=payload.get("storage_uri", ""),
            sha256_hash=payload.get("sha256_hash", ""),
            provenance=payload.get("provenance", {}),
            managed_by=payload.get("managed_by", "retrace"),
            page_number=payload.get("page_number"),
            row_start=payload.get("row_start"),
            row_end=payload.get("row_end"),
            timestamp=payload.get("timestamp"),
        )


class SemanticSearchRequest(BaseModel):
    """Request payload for evidence semantic similarity retrieval."""
    query: str = Field(..., min_length=1, max_length=1000, description="Troubleshooting search query")
    top_k: int = Field(default=8, ge=1, le=20, description="Max results to return (capped at 20)")
    asset_id: Optional[str] = Field(default=None, description="Optional asset ID filter")
    source_type: Optional[str] = Field(default=None, description="Optional source type filter")


class SemanticSearchResultItem(BaseModel):
    """Single ranked evidence chunk result.

    Note: The similarity metric is strictly 'similarity_score', NEVER confidence, certainty, or probability.
    """
    similarity_score: float = Field(..., description="Cosine similarity score (not confidence/probability)")
    evidence_id: str
    chunk_id: str
    asset_id: Optional[str] = None
    source_type: str
    filename: str
    text: str
    provenance: Dict[str, Any] = Field(default_factory=dict)


class SemanticSearchResponse(BaseModel):
    """Response payload for semantic search."""
    incident_id: str
    query: str
    results: List[SemanticSearchResultItem]


class VectorSyncResponse(BaseModel):
    """Response payload for incident vector synchronization."""
    incident_id: str
    evidence_processed: int
    chunks_indexed: int
    collection: str
    status: str
