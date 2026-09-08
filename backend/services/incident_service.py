"""Incident Service for retrieving incident timelines, topological assets, and findings."""
from typing import List, Optional
from backend.data.mock_data import (
    MOCK_INCIDENTS,
    MOCK_ASSETS,
    MOCK_ASSET_RELATIONSHIPS,
    MOCK_TIMELINE_EVENTS,
    MOCK_FINDINGS,
    MOCK_PREVENTION_SCENARIO,
    MOCK_EVIDENCE,
)
from backend.schemas.incident import Incident, IncidentEvent
from backend.schemas.asset import Asset, AssetRelationship
from backend.schemas.finding import Finding
from backend.schemas.prevention import PreventionScenario
from backend.schemas.context import IncidentContextResponse
from backend.schemas.evidence import Evidence

class IncidentService:
    @staticmethod
    def get_all_incidents() -> List[Incident]:
        return [Incident(**inc) for inc in MOCK_INCIDENTS]

    @staticmethod
    def get_incident_by_id(incident_id: str) -> Optional[Incident]:
        for inc in MOCK_INCIDENTS:
            if inc["id"].upper() == incident_id.upper():
                return Incident(**inc)
        return None

    @staticmethod
    def get_incident_events(incident_id: str) -> List[IncidentEvent]:
        events = [
            IncidentEvent(**evt)
            for evt in MOCK_TIMELINE_EVENTS
            if evt.get("incidentId", "").upper() == incident_id.upper()
        ]
        # Return timeline events sorted by normalized timestamp / relativeSeconds
        return sorted(events, key=lambda e: e.relative_seconds)

    @staticmethod
    def get_incident_assets(incident_id: str) -> List[Asset]:
        # In current prototype, assets are bound to INC-2026-001 cascade
        return [Asset(**asset) for asset in MOCK_ASSETS]

    @staticmethod
    def get_asset_relationships(incident_id: str) -> List[AssetRelationship]:
        return [AssetRelationship(**rel) for rel in MOCK_ASSET_RELATIONSHIPS]

    @staticmethod
    def get_incident_findings(incident_id: str) -> List[Finding]:
        return [
            Finding(**fnd)
            for fnd in MOCK_FINDINGS
            if fnd.get("incidentId", "").upper() == incident_id.upper()
        ]

    @staticmethod
    def get_incident_evidence(incident_id: str) -> List[Evidence]:
        # In demo, all 6 evidence items ground INC-2026-001
        return [Evidence(**evd) for evd in MOCK_EVIDENCE]

    @staticmethod
    def get_incident_context(incident_id: str) -> Optional[IncidentContextResponse]:
        incident = IncidentService.get_incident_by_id(incident_id)
        if not incident:
            return None

        events = IncidentService.get_incident_events(incident_id)
        assets = IncidentService.get_incident_assets(incident_id)
        relationships = IncidentService.get_asset_relationships(incident_id)
        evidence = IncidentService.get_incident_evidence(incident_id)
        findings = IncidentService.get_incident_findings(incident_id)

        return IncidentContextResponse(
            incident=incident,
            events=events,
            assets=assets,
            relationships=relationships,
            evidence=evidence,
            findings=findings,
        )

    @staticmethod
    def get_prevention_scenario(incident_id: str) -> Optional[PreventionScenario]:
        if incident_id.upper() != "INC-2026-001":
            return None
        return PreventionScenario(**MOCK_PREVENTION_SCENARIO)

incident_service = IncidentService()
