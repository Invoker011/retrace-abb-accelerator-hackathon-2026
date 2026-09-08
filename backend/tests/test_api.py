"""Tests for RETRACE FastAPI backend endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoint():
    """Verify health check returns status healthy and service name."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "RETRACE API"

def test_list_incidents():
    """Verify list incidents returns at least the primary synthetic incident."""
    response = client.get("/api/incidents")
    assert response.status_code == 200
    incidents = response.json()
    assert isinstance(incidents, list)
    assert len(incidents) >= 1
    assert any(inc["id"] == "INC-2026-001" for inc in incidents)

def test_get_incident_by_id():
    """Verify detail retrieval for INC-2026-001."""
    response = client.get("/api/incidents/INC-2026-001")
    assert response.status_code == 200
    incident = response.json()
    assert incident["id"] == "INC-2026-001"
    assert "Pump P-204" in incident["title"]
    assert incident["severity"] == "High"
    assert incident["status"] == "Under Investigation"

def test_get_unknown_incident_returns_404():
    """Verify 404 is returned for an unknown incident."""
    response = client.get("/api/incidents/INC-UNKNOWN-999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_get_incident_events():
    """Verify incident timeline events are returned and sorted."""
    response = client.get("/api/incidents/INC-2026-001/events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 5
    # Verify chronological ordering by relativeSeconds
    seconds = [e["relativeSeconds"] for e in events]
    assert seconds == sorted(seconds)
    assert events[0]["eventType"] == "warning"
    assert events[-1]["eventType"] == "alarm"

def test_get_incident_assets_and_relationships():
    """Verify assets and topology relationships for INC-2026-001."""
    assets_res = client.get("/api/incidents/INC-2026-001/assets")
    assert assets_res.status_code == 200
    assets = assets_res.json()
    assert len(assets) == 4
    asset_ids = {a["id"] for a in assets}
    assert {"VFD-204", "M-204", "P-204", "PLC-204"}.issubset(asset_ids)

    rel_res = client.get("/api/incidents/INC-2026-001/relationships")
    assert rel_res.status_code == 200
    rels = rel_res.json()
    assert len(rels) >= 3

def test_get_incident_findings_classification():
    """Verify findings preserve strict OBSERVED / CORRELATED / HYPOTHESIS / UNKNOWN categories."""
    response = client.get("/api/incidents/INC-2026-001/findings")
    assert response.status_code == 200
    findings = response.json()
    assert len(findings) >= 5
    categories = {f["category"] for f in findings}
    assert "OBSERVED" in categories
    assert "CORRELATED" in categories
    assert "HYPOTHESIS" in categories
    assert "UNKNOWN" in categories

def test_get_incident_context():
    """Verify single combined incident context response."""
    response = client.get("/api/incidents/INC-2026-001/context")
    assert response.status_code == 200
    context = response.json()
    assert "incident" in context
    assert "events" in context
    assert "assets" in context
    assert "relationships" in context
    assert "evidence" in context
    assert "findings" in context
    assert context["incident"]["id"] == "INC-2026-001"
    assert len(context["events"]) == 5
    assert len(context["assets"]) == 4

def test_get_evidence_provenance():
    """Verify evidence retrieval with full provenance."""
    response = client.get("/api/evidence/EVD-001")
    assert response.status_code == 200
    evidence = response.json()
    assert evidence["id"] == "EVD-001"
    assert evidence["filename"] == "VFD_204_Log.csv"
    assert evidence["confidence"] == 99.0
    assert "original_reference" in evidence or "originalReference" in evidence or "originalEvidenceRef" in evidence

    # Non-existent evidence 404
    res_404 = client.get("/api/evidence/EVD-NONEXISTENT")
    assert res_404.status_code == 404

def test_get_prevention_scenario():
    """Verify counterfactual prevention scenario and mandatory disclaimer."""
    response = client.get("/api/incidents/INC-2026-001/prevention")
    assert response.status_code == 200
    scenario = response.json()
    assert scenario["incidentId"] == "INC-2026-001"
    assert "actualPath" in scenario or "actual_path" in scenario
    assert (
        "This is an exploratory prevention scenario. RETRACE does not claim that the proposed "
        "intervention would definitely have prevented the incident."
    ) in scenario["disclaimer"]
    assert len(scenario["safeguards"]) >= 3

def test_investigation_query():
    """Verify deterministic mock investigation query endpoint."""
    payload = {
        "incident_id": "INC-2026-001",
        "question": "Why did Pump P-204 shut down?",
    }
    response = client.post("/api/investigation/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "findings" in data
    assert "supporting_evidence" in data or "supportingEvidence" in data
    assert data["classification"] == "CORRELATED"
    assert "unresolved_questions" in data or "unresolvedQuestions" in data
    assert len(data.get("unresolved_questions", data.get("unresolvedQuestions", []))) >= 1
