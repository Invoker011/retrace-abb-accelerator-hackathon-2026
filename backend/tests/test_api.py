"""Tests for RETRACE FastAPI backend endpoints."""
import unittest

try:
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    HAS_TESTCLIENT = True
except Exception:
    client = None  # type: ignore
    HAS_TESTCLIENT = False

from backend.data.mock_data import (
    MOCK_INCIDENTS,
    MOCK_TIMELINE_EVENTS,
    MOCK_ASSETS,
    MOCK_ASSET_RELATIONSHIPS,
    MOCK_FINDINGS,
    MOCK_EVIDENCE,
    MOCK_PREVENTION_SCENARIO,
)


class TestApiEndpoints(unittest.TestCase):
    def test_mock_data_integrity(self):
        """Verify baseline data integrity regardless of network client availability."""
        self.assertGreaterEqual(len(MOCK_INCIDENTS), 1)
        self.assertEqual(MOCK_INCIDENTS[0]["id"], "INC-2026-001")
        self.assertEqual(len(MOCK_TIMELINE_EVENTS), 5)
        self.assertEqual(len(MOCK_ASSETS), 4)
        self.assertGreaterEqual(len(MOCK_ASSET_RELATIONSHIPS), 3)
        self.assertGreaterEqual(len(MOCK_FINDINGS), 5)
        self.assertGreaterEqual(len(MOCK_EVIDENCE), 5)
        self.assertIsNotNone(MOCK_PREVENTION_SCENARIO)

    @unittest.skipUnless(HAS_TESTCLIENT, "TestClient requires httpx")
    def test_health_endpoint(self):
        """Verify health check returns status healthy and service name."""
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "RETRACE API")

    @unittest.skipUnless(HAS_TESTCLIENT, "TestClient requires httpx")
    def test_list_incidents(self):
        """Verify list incidents returns at least the primary synthetic incident."""
        response = client.get("/api/incidents")
        self.assertEqual(response.status_code, 200)
        incidents = response.json()
        self.assertIsInstance(incidents, list)
        self.assertGreaterEqual(len(incidents), 1)
        self.assertTrue(any(inc["id"] == "INC-2026-001" for inc in incidents))

    @unittest.skipUnless(HAS_TESTCLIENT, "TestClient requires httpx")
    def test_get_incident_by_id(self):
        """Verify detail retrieval for INC-2026-001."""
        response = client.get("/api/incidents/INC-2026-001")
        self.assertEqual(response.status_code, 200)
        incident = response.json()
        self.assertEqual(incident["id"], "INC-2026-001")
        self.assertIn("Pump P-204", incident["title"])
        self.assertEqual(incident["severity"], "High")
        self.assertEqual(incident["status"], "Under Investigation")

    @unittest.skipUnless(HAS_TESTCLIENT, "TestClient requires httpx")
    def test_get_unknown_incident_returns_404(self):
        """Verify 404 is returned for an unknown incident."""
        response = client.get("/api/incidents/INC-UNKNOWN-999")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())

    @unittest.skipUnless(HAS_TESTCLIENT, "TestClient requires httpx")
    def test_get_incident_events(self):
        """Verify incident timeline events are returned and sorted."""
        response = client.get("/api/incidents/INC-2026-001/events")
        self.assertEqual(response.status_code, 200)
        events = response.json()
        self.assertEqual(len(events), 5)
        seconds = [e["relativeSeconds"] for e in events]
        self.assertEqual(seconds, sorted(seconds))
        self.assertEqual(events[0]["eventType"], "warning")
        self.assertEqual(events[-1]["eventType"], "alarm")

    @unittest.skipUnless(HAS_TESTCLIENT, "TestClient requires httpx")
    def test_get_incident_assets_and_relationships(self):
        """Verify assets and topology relationships for INC-2026-001."""
        assets_res = client.get("/api/incidents/INC-2026-001/assets")
        self.assertEqual(assets_res.status_code, 200)
        assets = assets_res.json()
        self.assertEqual(len(assets), 4)
        asset_ids = {a["id"] for a in assets}
        self.assertTrue({"VFD-204", "M-204", "P-204", "PLC-204"}.issubset(asset_ids))

        rel_res = client.get("/api/incidents/INC-2026-001/relationships")
        self.assertEqual(rel_res.status_code, 200)
        rels = rel_res.json()
        self.assertGreaterEqual(len(rels), 3)

    @unittest.skipUnless(HAS_TESTCLIENT, "TestClient requires httpx")
    def test_get_incident_findings_classification(self):
        """Verify findings preserve strict OBSERVED / CORRELATED / HYPOTHESIS / UNKNOWN categories."""
        response = client.get("/api/incidents/INC-2026-001/findings")
        self.assertEqual(response.status_code, 200)
        findings = response.json()
        self.assertGreaterEqual(len(findings), 5)
        categories = {f["category"] for f in findings}
        self.assertIn("OBSERVED", categories)
        self.assertIn("CORRELATED", categories)
        self.assertIn("HYPOTHESIS", categories)
        self.assertIn("UNKNOWN", categories)

    @unittest.skipUnless(HAS_TESTCLIENT, "TestClient requires httpx")
    def test_get_incident_context(self):
        """Verify single combined incident context response."""
        response = client.get("/api/incidents/INC-2026-001/context")
        self.assertEqual(response.status_code, 200)
        context = response.json()
        self.assertIn("incident", context)
        self.assertIn("events", context)
        self.assertIn("assets", context)
        self.assertIn("relationships", context)
        self.assertIn("evidence", context)
        self.assertIn("findings", context)
        self.assertEqual(context["incident"]["id"], "INC-2026-001")
        self.assertEqual(len(context["events"]), 5)
        self.assertEqual(len(context["assets"]), 4)

    @unittest.skipUnless(HAS_TESTCLIENT, "TestClient requires httpx")
    def test_get_evidence_provenance(self):
        """Verify evidence retrieval with full provenance."""
        response = client.get("/api/evidence/EVD-001")
        self.assertEqual(response.status_code, 200)
        evidence = response.json()
        self.assertEqual(evidence["id"], "EVD-001")
        self.assertEqual(evidence["filename"], "VFD_204_Log.csv")
        self.assertEqual(evidence["confidence"], 99.0)

        res_404 = client.get("/api/evidence/EVD-NONEXISTENT")
        self.assertEqual(res_404.status_code, 404)

    @unittest.skipUnless(HAS_TESTCLIENT, "TestClient requires httpx")
    def test_get_prevention_scenario(self):
        """Verify counterfactual prevention scenario and mandatory disclaimer."""
        response = client.get("/api/incidents/INC-2026-001/prevention")
        self.assertEqual(response.status_code, 200)
        scenario = response.json()
        self.assertEqual(scenario["incidentId"], "INC-2026-001")
        self.assertIn(
            "This is an exploratory prevention scenario. RETRACE does not claim that the proposed "
            "intervention would definitely have prevented the incident.",
            scenario["disclaimer"],
        )
        self.assertGreaterEqual(len(scenario["safeguards"]), 3)

    @unittest.skipUnless(HAS_TESTCLIENT, "TestClient requires httpx")
    def test_investigation_query(self):
        """Verify deterministic mock investigation query endpoint."""
        payload = {
            "incident_id": "INC-2026-001",
            "question": "Why did Pump P-204 shut down?",
        }
        response = client.post("/api/investigation/query", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("answer", data)
        self.assertIn("findings", data)
        self.assertEqual(data["classification"], "CORRELATED")


if __name__ == "__main__":
    unittest.main()

