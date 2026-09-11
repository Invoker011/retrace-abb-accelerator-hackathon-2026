"""Pydantic schemas for RETRACE Hybrid Retrieval layer."""
from typing import Any, Dict, List, Optional
from backend.schemas.base import BaseModel, Field


class HybridSearchRequest(BaseModel):
    """Request payload for hybrid evidence retrieval."""
    query: str = Field(..., min_length=1, max_length=1000, description="Technician / investigator search query")
    top_k: int = Field(default=8, ge=1, le=20, description="Number of fused evidence results to return (capped at 20)")
    asset_id: Optional[str] = Field(default=None, description="Optional asset ID filter (e.g., 'VFD-204')")
    source_type: Optional[str] = Field(default=None, description="Optional source type filter")


class HybridEvidenceResult(BaseModel):
    """Single deduplicated evidence chunk with fused RRF ranking and channel attribution.

    Note: The metric is strictly 'retrieval_score', NEVER confidence, certainty, or probability.
    """
    rank: int = Field(..., description="1-based fused ranking position")
    retrieval_score: float = Field(..., description="Deterministic Reciprocal Rank Fusion (RRF) score")
    retrieval_channels: List[str] = Field(
        default_factory=list,
        description="Retrieval channels that surfaced this item, e.g. ['semantic', 'keyword', 'identifier']"
    )

    semantic_rank: Optional[int] = Field(default=None, description="1-based rank in semantic vector channel if retrieved")
    similarity_score: Optional[float] = Field(default=None, description="Cosine similarity score from Qdrant vector retrieval")

    keyword_rank: Optional[int] = Field(default=None, description="1-based rank in lexical channel if retrieved")
    keyword_score: Optional[float] = Field(default=None, description="Deterministic lexical relevance score")

    evidence_id: str = Field(..., description="Parent evidence identifier (e.g., 'EVD-001')")
    chunk_id: str = Field(..., description="Unique chunk identifier (e.g., 'EVD-001-chk-0')")

    asset_id: Optional[str] = Field(default=None, description="Associated industrial asset tag")
    filename: str = Field(..., description="Original evidence filename or document source")
    source_type: str = Field(..., description="Industrial evidence source category")
    text: str = Field(..., description="Factual extracted text content of the chunk")
    timestamp: Optional[str] = Field(default=None, description="Original or normalized timestamp of the evidence")

    provenance: Dict[str, Any] = Field(default_factory=dict, description="Metadata preserving exact data provenance")


class GraphContextAsset(BaseModel):
    """Asset node included in the enriched context graph."""
    id: str
    name: str
    type: str
    criticality: Optional[str] = None
    status: Optional[str] = None


class GraphContextRelationship(BaseModel):
    """Edge included in the enriched context graph."""
    source: str
    target: str
    relationship: str
    description: Optional[str] = None


class GraphContext(BaseModel):
    """Bounded subgraph context connecting physical equipment and evidence."""
    assets: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)


class TemporalContextItem(BaseModel):
    """Chronological event in the incident timeline relevant to retrieved evidence."""
    event_id: str = Field(..., description="Unique incident event ID (e.g., 'EVT-001')")
    timestamp: str = Field(..., description="Normalized ISO-8601 timestamp")
    relative_seconds: Optional[int] = Field(default=None, description="Elapsed seconds from incident inception")
    asset_id: str = Field(..., description="Asset where event occurred")
    title: str = Field(..., description="Event summary title")
    event_type: str = Field(..., description="Event type classification (e.g. warning, alarm, deviation)")
    severity: str = Field(..., description="Severity level")
    evidence_id: Optional[str] = Field(default=None, description="Directly supporting evidence ID if linked")


class HybridSearchResponse(BaseModel):
    """Grounded context package assembling semantic, lexical, graph, and temporal context."""
    incident_id: str
    query: str
    recognized_identifiers: List[str] = Field(default_factory=list)
    evidence: List[HybridEvidenceResult] = Field(default_factory=list)
    graph_context: Dict[str, Any] = Field(default_factory=dict)
    temporal_context: List[TemporalContextItem] = Field(default_factory=list)
