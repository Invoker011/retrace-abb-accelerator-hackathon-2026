"""Incident Replay schemas for RETRACE.

Provides structured models for forensic chronological reconstruction of industrial incidents.
Guarantees:
  - Distinguishes recorded events, state changes, involved assets, and supporting evidence
  - Deterministic phases (PRECURSOR, DEGRADATION, OPERATOR_OBSERVATION, PROTECTIVE_SHUTDOWN, UNCLASSIFIED)
  - Topology relationships surfaced as physical connections only (zero causal language)
  - Forensic reconstruction without causal simulation or invented data
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from backend.schemas.base import BaseModel, Field


class ReplayPhase(str, Enum):
    """Deterministic operational phases of an industrial incident."""
    PRECURSOR = "PRECURSOR"
    DEGRADATION = "DEGRADATION"
    OPERATOR_OBSERVATION = "OPERATOR_OBSERVATION"
    PROTECTIVE_SHUTDOWN = "PROTECTIVE_SHUTDOWN"
    UNCLASSIFIED = "UNCLASSIFIED"


class ReplayEvidenceReference(BaseModel):
    """Direct reference to evidence supporting a recorded replay event."""
    evidence_id: str = Field(..., alias="evidenceId")
    filename: str
    source_type: str = Field(..., alias="sourceType")
    asset_id: Optional[str] = Field(default=None, alias="assetId")
    timestamp: Optional[str] = None
    original_reference: Optional[str] = Field(default=None, alias="originalReference")

    class Config:
        populate_by_name = True


class ReplayRecordedValue(BaseModel):
    """Factual telemetry or observation measurement recorded in evidence."""
    name: str
    value: Any
    unit: Optional[str] = None
    source_evidence_id: Optional[str] = Field(default=None, alias="sourceEvidenceId")

    class Config:
        populate_by_name = True


class ReplayRelationshipContext(BaseModel):
    """Topological equipment coupling context (strictly non-causal)."""
    source: str
    relationship: str
    target: str
    description: Optional[str] = None

    class Config:
        populate_by_name = True


class ReplayAssetState(BaseModel):
    """Factual asset status and recorded telemetry values at event time."""
    asset_id: str = Field(..., alias="assetId")
    asset_name: Optional[str] = Field(default=None, alias="assetName")
    operational_status: Optional[str] = Field(default=None, alias="operationalStatus")
    recorded_values: List[ReplayRecordedValue] = Field(default_factory=list, alias="recordedValues")

    class Config:
        populate_by_name = True


class ReplayEvent(BaseModel):
    """Chronologically reconstructed incident event."""
    sequence: int
    event_id: str = Field(..., alias="eventId")
    timestamp: str
    relative_seconds: int = Field(..., alias="relativeSeconds")
    asset_id: str = Field(..., alias="assetId")
    title: str
    event_type: str = Field(..., alias="eventType")
    severity: str
    phase: ReplayPhase
    description: str
    evidence: List[ReplayEvidenceReference] = Field(default_factory=list)
    related_assets: List[str] = Field(default_factory=list, alias="relatedAssets")
    graph_relationships: List[ReplayRelationshipContext] = Field(
        default_factory=list, alias="graphRelationships"
    )
    asset_state: Optional[ReplayAssetState] = Field(default=None, alias="assetState")
    recorded_values: List[ReplayRecordedValue] = Field(
        default_factory=list, alias="recordedValues"
    )

    class Config:
        populate_by_name = True


class ReplaySummary(BaseModel):
    """Deterministic summary metrics for replay reconstruction."""
    event_count: int = Field(..., alias="eventCount")
    asset_count: int = Field(..., alias="assetCount")
    evidence_count: int = Field(..., alias="evidenceCount")
    duration_seconds: int = Field(..., alias="durationSeconds")

    class Config:
        populate_by_name = True


class ReplayWindowFilter(BaseModel):
    """Optional time window applied to replay sequence."""
    start_offset_seconds: Optional[int] = Field(default=None, alias="startOffsetSeconds")
    end_offset_seconds: Optional[int] = Field(default=None, alias="endOffsetSeconds")

    class Config:
        populate_by_name = True


class IncidentReplayResponse(BaseModel):
    """Full deterministic forensic incident replay response."""
    incident_id: str = Field(..., alias="incidentId")
    start_timestamp: Optional[str] = Field(default=None, alias="startTimestamp")
    end_timestamp: Optional[str] = Field(default=None, alias="endTimestamp")
    duration_seconds: int = Field(..., alias="durationSeconds")
    summary: ReplaySummary
    events: List[ReplayEvent] = Field(default_factory=list)
    window_filter: Optional[ReplayWindowFilter] = Field(default=None, alias="windowFilter")

    class Config:
        populate_by_name = True
