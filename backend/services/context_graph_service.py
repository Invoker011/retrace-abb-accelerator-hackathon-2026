"""Context Graph Service.

Orchestrates synchronization between industrial evidence/incident domains (from PostgreSQL
and synthetic services) and the Neo4j Incident Context Graph.
"""
import logging
import re
from typing import Any, Dict, List, Optional

from backend.core.config import settings
from backend.services.incident_service import incident_service
from backend.repositories.uploaded_evidence_repository import get_uploaded_evidence_repository
from backend.repositories.incident_graph_repository import (
    IncidentGraphRepositoryInterface,
    get_incident_graph_repository,
)

logger = logging.getLogger(__name__)

SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-\.]+$")


class ContextGraphError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ContextGraphService:
    """Provides high-level graph synchronization and query capabilities."""

    def __init__(self, repo: Optional[IncidentGraphRepositoryInterface] = None):
        self._repo = repo

    @property
    def repo(self) -> IncidentGraphRepositoryInterface:
        if self._repo is not None:
            return self._repo
        return get_incident_graph_repository()

    def sync_incident_context(self, incident_id: str) -> Dict[str, Any]:
        """Synchronize the incident, operational events, assets, findings, and evidence into Neo4j."""
        if not incident_id or not SAFE_ID_PATTERN.match(incident_id):
            raise ContextGraphError(f"Invalid incident ID format: '{incident_id}'", status_code=400)

        # 1. Retrieve incident data using existing incident service
        incident = incident_service.get_incident_by_id(incident_id)
        if not incident:
            raise ContextGraphError(f"Incident '{incident_id}' not found.", status_code=404)

        assets = incident_service.get_incident_assets(incident_id)
        events = incident_service.get_incident_events(incident_id)
        synthetic_evidence = incident_service.get_incident_evidence(incident_id)
        findings = incident_service.get_incident_findings(incident_id)
        relationships = incident_service.get_asset_relationships(incident_id)

        # 2. Retrieve persistent uploaded evidence metadata from PostgreSQL
        uploaded_repo = get_uploaded_evidence_repository()
        try:
            uploaded_records = uploaded_repo.get_by_incident(incident_id)
        except Exception as e:
            logger.warning("[RETRACE] Could not retrieve uploaded evidence for graph sync: %s", type(e).__name__)
            uploaded_records = []

        # Combine synthetic baseline evidence with persistent uploaded evidence
        evidence_dicts: List[Dict[str, Any]] = [
            ev.model_dump() if hasattr(ev, "model_dump") else ev.dict() if hasattr(ev, "dict") else dict(ev)
            for ev in synthetic_evidence
        ]

        for upl in uploaded_records:
            upl_dict = upl.model_dump() if hasattr(upl, "model_dump") else upl.dict() if hasattr(upl, "dict") else dict(upl)
            evidence_dicts.append({
                "id": upl_dict.get("evidence_id"),
                "evidence_id": upl_dict.get("evidence_id"),
                "sourceType": upl_dict.get("source_type"),
                "source_type": upl_dict.get("source_type"),
                "filename": upl_dict.get("original_filename"),
                "original_filename": upl_dict.get("original_filename"),
                "processingStatus": upl_dict.get("processing_status", "UPLOADED"),
                "processing_status": upl_dict.get("processing_status", "UPLOADED"),
                "assetId": upl_dict.get("asset_id"),
                "asset_id": upl_dict.get("asset_id"),
            })

        # Convert schemas to dicts
        inc_dict = incident.model_dump() if hasattr(incident, "model_dump") else incident.dict()
        asset_dicts = [a.model_dump() if hasattr(a, "model_dump") else a.dict() for a in assets]
        event_dicts = [e.model_dump() if hasattr(e, "model_dump") else e.dict() for e in events]
        finding_dicts = [f.model_dump() if hasattr(f, "model_dump") else f.dict() for f in findings]
        rel_dicts = [r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in relationships]

        try:
            return self.repo.sync_incident(
                incident=inc_dict,
                assets=asset_dicts,
                events=event_dicts,
                evidence=evidence_dicts,
                findings=finding_dicts,
                relationships=rel_dicts,
            )
        except Exception as e:
            if isinstance(e, ContextGraphError):
                raise
            logger.error("[RETRACE] Graph synchronization failed: %s", type(e).__name__)
            status_code = 503 if settings.ENVIRONMENT == "production" else 500
            raise ContextGraphError(
                f"Failed to synchronize incident context graph: {str(e)}",
                status_code=status_code,
            )

    def get_incident_graph(self, incident_id: str) -> Dict[str, Any]:
        """Retrieve frontend-friendly graph structure (nodes and edges)."""
        if not incident_id or not SAFE_ID_PATTERN.match(incident_id):
            raise ContextGraphError(f"Invalid incident ID format: '{incident_id}'", status_code=400)

        incident = incident_service.get_incident_by_id(incident_id)
        if not incident:
            raise ContextGraphError(f"Incident '{incident_id}' not found.", status_code=404)

        try:
            return self.repo.get_incident_subgraph(incident_id)
        except Exception as e:
            logger.warning("[RETRACE] Failed to query graph repository: %s", type(e).__name__)
            # In development mode, graceful fallback to mock graph
            if settings.ENVIRONMENT != "production":
                from backend.repositories.incident_graph_repository import InMemoryIncidentGraphRepository
                fallback_repo = InMemoryIncidentGraphRepository()
                return fallback_repo.get_incident_subgraph(incident_id)
            raise ContextGraphError("Graph database is currently unavailable.", status_code=503)

    def find_asset_path(
        self, incident_id: str, source_asset: str, target_asset: str
    ) -> Dict[str, Any]:
        """Find relationship path between two assets without arbitrary Cypher execution."""
        if not incident_id or not SAFE_ID_PATTERN.match(incident_id):
            raise ContextGraphError(f"Invalid incident ID format: '{incident_id}'", status_code=400)
        if not source_asset or not SAFE_ID_PATTERN.match(source_asset):
            raise ContextGraphError(f"Invalid source asset ID format: '{source_asset}'", status_code=400)
        if not target_asset or not SAFE_ID_PATTERN.match(target_asset):
            raise ContextGraphError(f"Invalid target asset ID format: '{target_asset}'", status_code=400)

        try:
            return self.repo.find_asset_path(incident_id, source_asset, target_asset)
        except Exception as e:
            logger.warning("[RETRACE] Asset path query failed: %s", type(e).__name__)
            if settings.ENVIRONMENT != "production":
                from backend.repositories.incident_graph_repository import InMemoryIncidentGraphRepository
                fallback_repo = InMemoryIncidentGraphRepository()
                return fallback_repo.find_asset_path(incident_id, source_asset, target_asset)
            raise ContextGraphError("Graph path discovery failed or graph is unavailable.", status_code=503)


# Singleton service instance
context_graph_service = ContextGraphService()
