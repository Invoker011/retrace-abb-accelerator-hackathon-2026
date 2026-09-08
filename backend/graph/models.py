"""Domain constants, node schemas, and API response models for the Context Graph."""
from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:  # type: ignore
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def dict(self):
            return self.__dict__
        def model_dump(self):
            return self.__dict__

    def Field(default=None, default_factory=None, **kwargs):  # type: ignore
        if default_factory is not None:
            return default_factory()
        return default

# Node Labels
LABEL_INCIDENT = "Incident"
LABEL_ASSET = "Asset"
LABEL_EVENT = "Event"
LABEL_EVIDENCE = "Evidence"
LABEL_FINDING = "Finding"

# Canonical Canonical Relationship Types (Uppercase)
REL_INVOLVES = "INVOLVES"
REL_HAS_EVENT = "HAS_EVENT"
REL_HAS_EVIDENCE = "HAS_EVIDENCE"
REL_HAS_FINDING = "HAS_FINDING"
REL_OCCURRED_ON = "OCCURRED_ON"
REL_SUPPORTED_BY = "SUPPORTED_BY"
REL_RELATES_TO = "RELATES_TO"
REL_POWERS = "POWERS"
REL_DRIVES = "DRIVES"
REL_MONITORED_BY = "MONITORED_BY"
REL_RELATED_TO = "RELATED_TO"


# Frontend-friendly Graph Node
class GraphNode(BaseModel):
    id: str
    type: str = Field(..., description="Node label (incident, asset, event, evidence, finding)")
    label: str = Field(..., description="Human-readable display title or name")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Searchable node properties")


# Frontend-friendly Graph Edge
class GraphEdge(BaseModel):
    id: str
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relationship: str = Field(..., description="Canonical uppercase relationship type")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Edge metadata")


# Response model for GET /api/incidents/{incident_id}/graph
class GraphResponse(BaseModel):
    incident_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    source: str = Field("neo4j", description="'neo4j' for live persistent graph, or 'mock' for development fallback")


# Response model for POST /api/incidents/{incident_id}/graph/sync
class GraphSyncResponse(BaseModel):
    incident_id: str
    nodes_created_or_matched: int
    relationships_created_or_matched: int
    status: str = "synchronized"


# Response model for GET /api/incidents/{incident_id}/graph/paths
class AssetPathResponse(BaseModel):
    incident_id: str
    source_asset: str
    target_asset: str
    found: bool
    path: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)
    length: int = 0
