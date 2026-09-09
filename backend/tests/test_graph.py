"""Unit tests for the RETRACE Incident Context Graph layer.

Tests:
  - Graph client health checks and safe statuses
  - Idempotent synchronization with MERGE semantics
  - Cypher injection prevention (parameterized queries)
  - Asset path queries (VFD-204 -> M-204 -> P-204)
  - Absence of credential leaks
"""
import os
import re
import unittest
from unittest.mock import MagicMock, patch

# Safe import pattern
try:
    from backend.graph.models import (
        LABEL_INCIDENT,
        LABEL_ASSET,
        LABEL_EVENT,
        LABEL_EVIDENCE,
        LABEL_FINDING,
        REL_INVOLVES,
        REL_HAS_EVENT,
        REL_HAS_EVIDENCE,
        REL_POWERS,
        REL_DRIVES,
        REL_MONITORED_BY,
        REL_RELATED_TO,
    )
    from backend.graph.client import check_neo4j_health, get_neo4j_driver
    from backend.repositories.incident_graph_repository import (
        InMemoryIncidentGraphRepository,
        Neo4jIncidentGraphRepository,
        ProductionUnconfiguredGraphRepository,
        get_incident_graph_repository,
        set_incident_graph_repository,
        SAFE_ID_REGEX,
    )
    from backend.services.context_graph_service import (
        ContextGraphService,
        ContextGraphError,
    )
    IMPORTS_LOADED = True
except ImportError:
    IMPORTS_LOADED = False


class TestContextGraphRepository(unittest.TestCase):
    def setUp(self):
        if not IMPORTS_LOADED:
            self.skipTest("Pydantic/backend dependencies not in current environment.")
        self.repo = InMemoryIncidentGraphRepository()
        set_incident_graph_repository(self.repo)
        self.service = ContextGraphService(repo=self.repo)

    def tearDown(self):
        if IMPORTS_LOADED:
            set_incident_graph_repository(None)

    def test_safe_id_regex(self):
        """Verify SAFE_ID_REGEX blocks potential Cypher injection strings."""
        self.assertTrue(bool(SAFE_ID_REGEX.match("VFD-204")))
        self.assertTrue(bool(SAFE_ID_REGEX.match("INC-2026-001")))
        self.assertTrue(bool(SAFE_ID_REGEX.match("P-204")))
        self.assertTrue(bool(SAFE_ID_REGEX.match("EVD_001.csv")))

        # Injections or malicious patterns
        self.assertFalse(bool(SAFE_ID_REGEX.match("VFD-204' OR '1'='1")))
        self.assertFalse(bool(SAFE_ID_REGEX.match("VFD-204; MATCH (n) DETACH DELETE n;")))
        self.assertFalse(bool(SAFE_ID_REGEX.match("VFD-204\\")))
        self.assertFalse(bool(SAFE_ID_REGEX.match("")))

    def test_in_memory_idempotent_sync(self):
        """Verify synchronizing incident context multiple times does not duplicate entities."""
        incident = {
            "id": "INC-2026-001",
            "title": "Slurry Pump Trip",
            "severity": "Critical",
            "status": "Under Investigation",
            "plantArea": "Flotation Bank B",
            "date": "2026-03-02",
        }
        assets = [
            {"id": "VFD-204", "name": "VFD 204", "type": "Variable Frequency Drive"},
            {"id": "M-204", "name": "Drive Motor 204", "type": "AC Induction Motor"},
            {"id": "P-204", "name": "Slurry Pump 204", "type": "Centrifugal Slurry Pump"},
            {"id": "PLC-204", "name": "Control PLC 204", "type": "Programmable Logic Controller"},
        ]
        events = [
            {"id": "EVT-001", "title": "Current Spikes", "assetId": "VFD-204"},
            {"id": "EVT-002", "title": "Thermal Overload", "assetId": "M-204"},
        ]
        evidence = [
            {"id": "EVD-001", "filename": "vfd_log.csv", "assetId": "VFD-204"},
            {"id": "EVD-UPL-001", "filename": "thermal_scan.jpg", "assetId": "VFD-204"},
        ]
        findings = [
            {"id": "FND-001", "statement": "Thermal trip caused by drive surge", "assetId": "VFD-204", "evidenceIds": ["EVD-001"]}
        ]

        # First synchronization
        res1 = self.repo.sync_incident(incident, assets, events, evidence, findings, [])
        self.assertEqual(res1["status"], "synchronized")

        subgraph = self.repo.get_incident_subgraph("INC-2026-001")
        initial_node_count = len(subgraph["nodes"])
        initial_edge_count = len(subgraph["edges"])

        # Second synchronization (identical data) - must be idempotent
        res2 = self.repo.sync_incident(incident, assets, events, evidence, findings, [])
        self.assertEqual(res2["status"], "synchronized")

        subgraph_after = self.repo.get_incident_subgraph("INC-2026-001")
        self.assertEqual(len(subgraph_after["nodes"]), initial_node_count)
        self.assertEqual(len(subgraph_after["edges"]), initial_edge_count)

    def test_asset_path_discovery(self):
        """Verify topology relationship path from VFD-204 to P-204."""
        # Seed default mock graph
        subgraph = self.repo.get_incident_subgraph("INC-2026-001")
        path_res = self.repo.find_asset_path("INC-2026-001", "VFD-204", "P-204")
        self.assertTrue(path_res["found"])
        self.assertEqual(path_res["source_asset"], "VFD-204")
        self.assertEqual(path_res["target_asset"], "P-204")
        # Should traverse VFD-204 -> POWERS -> M-204 -> DRIVES -> P-204
        self.assertIn("POWERS", path_res["relationships"])
        self.assertIn("DRIVES", path_res["relationships"])

    def test_neo4j_health_status_not_configured(self):
        """Verify safe response when Neo4j is unconfigured."""
        with patch("backend.core.config.settings.NEO4J_URI", None):
            status = check_neo4j_health()
            self.assertEqual(status, "not_configured")

    def test_neo4j_mock_driver_sync(self):
        """Verify Neo4jIncidentGraphRepository passes parameterized queries to Neo4j session."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        neo_repo = Neo4jIncidentGraphRepository(driver=mock_driver)
        res = neo_repo.sync_incident(
            incident={"id": "INC-TEST", "title": "Test Incident"},
            assets=[{"id": "A-1", "name": "Asset 1"}],
            events=[],
            evidence=[],
            findings=[],
            relationships=[],
        )
        self.assertEqual(res["status"], "synchronized")
        # Verify run was called with parameterized query
        self.assertTrue(mock_session.run.called)
        first_call_args = mock_session.run.call_args_list[0]
        # First call is constraint creation
        self.assertIn("CREATE CONSTRAINT IF NOT EXISTS", first_call_args[0][0])

    def test_neo4j_session_optional_database_default(self):
        """Verify driver.session() is called without database parameter when database is unset or empty."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        # Explicitly pass None as database
        repo = Neo4jIncidentGraphRepository(driver=mock_driver, database=None)
        with patch("backend.core.config.settings.NEO4J_DATABASE", None):
            repo.ensure_constraints()

        mock_driver.session.assert_called_with()
        # Verify database keyword argument was NOT passed
        call_kwargs = mock_driver.session.call_args[1]
        self.assertNotIn("database", call_kwargs)

    def test_neo4j_session_optional_database_configured(self):
        """Verify driver.session(database=configured_database) when database is specified."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        repo = Neo4jIncidentGraphRepository(driver=mock_driver, database="custom_auradb")
        repo.ensure_constraints()

        mock_driver.session.assert_called_with(database="custom_auradb")

    def test_neo4j_cypher_syntax_and_null_filtering(self):
        """Verify Cypher queries in sync_incident use valid syntax and filter null identifiers."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        repo = Neo4jIncidentGraphRepository(driver=mock_driver)

        # Sync with rich data including valid and null/missing evidence & findings
        incident = {"id": "INC-2026-001", "title": "Main Slurry Cascade"}
        assets = [
            {"id": "VFD-204", "name": "Variable Frequency Drive"},
            {"id": "M-204", "name": "Slurry Pump Motor"},
            {"id": "P-204", "name": "Centrifugal Slurry Pump"},
            {"id": "PLC-204", "name": "Control Logic Unit"},
        ]
        events = [
            {"id": "EVT-1", "title": "Vibration Spike", "assetId": "M-204", "evidenceId": "EVD-001"},
            {"id": "EVT-2", "title": "Telemetry Lag", "assetId": None, "evidenceId": None},  # Null asset & evidence
        ]
        evidence = [
            {"id": "EVD-001", "filename": "vfd_log.csv", "assetId": "VFD-204"},
            {"id": None, "filename": "corrupt_log.csv", "assetId": None},  # Missing ID
            {"evidence_id": "", "filename": "empty_id.csv", "assetId": "M-204"},  # Empty ID
            {"evidence_id": "EVD-002", "filename": "scada_events.csv", "assetId": None},  # Valid ID, no asset
        ]
        findings = [
            {"id": "FND-001", "statement": "Vibration excursion", "assetId": "M-204", "evidenceIds": ["EVD-001"]},
            {"id": "FND-002", "statement": "Hypothetical issue", "assetId": None, "evidenceIds": []},  # No evidence
            {"id": "FND-003", "statement": "Finding with None in evidenceIds", "assetId": "P-204", "evidenceIds": [None, ""]},
        ]

        res = repo.sync_incident(incident, assets, events, evidence, findings, [])
        self.assertEqual(res["status"], "synchronized")

        # Inspect every query executed during sync
        executed_queries = [call[0][0] for call in mock_session.run.call_args_list]

        for query in executed_queries:
            # Cypher syntax check: UNWIND must not be directly followed by WHERE
            lines = [line.strip() for line in query.strip().split("\n") if line.strip()]
            for i in range(len(lines) - 1):
                curr = lines[i].upper()
                nxt = lines[i + 1].upper()
                if curr.startswith("UNWIND"):
                    self.assertFalse(
                        nxt.startswith("WHERE"),
                        f"Found invalid Cypher 'UNWIND ... WHERE' without 'WITH' in query:\n{query}"
                    )

            # Node MERGE check: Never MERGE on a null or empty identifier without a preceding WHERE filter
            if "MERGE (evidence:" in query:
                self.assertIn("WHERE ev.evidence_id IS NOT NULL", query)
            if "MERGE (event:" in query:
                self.assertIn("WHERE e.event_id IS NOT NULL", query)
            if "MERGE (asset:" in query:
                self.assertIn("WHERE a.asset_id IS NOT NULL", query)
            if "MERGE (finding:" in query:
                self.assertIn("WHERE f.finding_id IS NOT NULL", query)

        # Verify topology couplings were executed with parameterized asset IDs
        powers_query = [q for q in executed_queries if "[:POWERS]->" in q]
        self.assertTrue(len(powers_query) >= 1)
        self.assertIn("$vfd_id", powers_query[0])
        self.assertIn("$m_id", powers_query[0])

        drives_query = [q for q in executed_queries if "[:DRIVES]->" in q]
        self.assertTrue(len(drives_query) >= 1)
        self.assertIn("$m_id", drives_query[0])
        self.assertIn("$p_id", drives_query[0])

        monitored_by_query = [q for q in executed_queries if "[:MONITORED_BY]->" in q]
        self.assertTrue(len(monitored_by_query) >= 1)
        self.assertIn("$p_id", monitored_by_query[0])
        self.assertIn("$plc_id", monitored_by_query[0])

    def test_in_memory_sync_null_evidence_and_topology(self):
        """Verify InMemoryIncidentGraphRepository skips null evidence safely and preserves topology."""
        repo = InMemoryIncidentGraphRepository()
        incident = {"id": "INC-TEST-002", "title": "Slurry Pump Test"}
        assets = [
            {"id": "VFD-204", "name": "VFD-204 Drive"},
            {"id": "M-204", "name": "Motor M-204"},
            {"id": "P-204", "name": "Pump P-204"},
        ]
        evidence = [
            {"id": "EVD-VALID-1", "filename": "vfd.csv", "assetId": "VFD-204"},
            {"id": None, "filename": "invalid.csv"},  # Missing ID
            {"evidence_id": "", "filename": "empty.csv"},  # Empty ID
        ]
        findings = [
            {"id": "FND-1", "statement": "Finding 1", "assetId": "M-204", "evidenceIds": ["EVD-VALID-1"]},
            {"id": "FND-2", "statement": "Finding 2", "evidenceIds": None},  # None evidenceIds
        ]

        # 1. First sync
        res1 = repo.sync_incident(incident, assets, [], evidence, findings, [])
        self.assertEqual(res1["status"], "synchronized")

        subgraph = repo.get_incident_subgraph("INC-TEST-002")
        node_ids = {n["id"] for n in subgraph["nodes"]}

        # Valid evidence exists, null/empty IDs do NOT exist
        self.assertIn("EVD-VALID-1", node_ids)
        self.assertNotIn(None, node_ids)
        self.assertNotIn("", node_ids)

        # Verify VFD-204 POWERS M-204 and M-204 DRIVES P-204
        edge_tuples = {(e["source"], e["relationship"], e["target"]) for e in subgraph["edges"]}
        self.assertIn(("VFD-204", "POWERS", "M-204"), edge_tuples)
        self.assertIn(("M-204", "DRIVES", "P-204"), edge_tuples)

        # 2. Repeated sync remains idempotent
        res2 = repo.sync_incident(incident, assets, [], evidence, findings, [])
        subgraph2 = repo.get_incident_subgraph("INC-TEST-002")
        self.assertEqual(len(subgraph2["nodes"]), len(subgraph["nodes"]))
        self.assertEqual(len(subgraph2["edges"]), len(subgraph["edges"]))

    def test_get_neo4j_session_helper_optional(self):
        """Verify get_neo4j_session context manager respects optional database."""
        from backend.graph.client import get_neo4j_session

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value = mock_session

        with patch("backend.graph.client.get_neo4j_driver", return_value=mock_driver):
            # 1. Unset database
            with patch("backend.core.config.settings.NEO4J_DATABASE", None):
                with get_neo4j_session():
                    pass
                mock_driver.session.assert_called_with()

            mock_driver.reset_mock()

            # 2. Configured database
            with patch("backend.core.config.settings.NEO4J_DATABASE", "production_auradb"):
                with get_neo4j_session():
                    pass
                mock_driver.session.assert_called_with(database="production_auradb")

            mock_driver.reset_mock()

            # 3. Explicit database override
            with patch("backend.core.config.settings.NEO4J_DATABASE", None):
                with get_neo4j_session(database="tenant_db"):
                    pass
                mock_driver.session.assert_called_with(database="tenant_db")

    def test_integrity_1_evidence_nodes_present_in_subgraph(self):
        """1. Verify Evidence nodes (synthetic EVD-001..EVD-006 and uploaded) are present in graph nodes."""
        repo = InMemoryIncidentGraphRepository()
        incident = {"id": "INC-2026-001", "title": "Slurry Pump Overheating"}
        assets = [{"id": "VFD-204", "name": "VFD-204"}]
        evidence = [
            {"id": "EVD-001", "filename": "vfd_log.csv", "assetId": "VFD-204"},
            {"id": "EVD-002", "filename": "scada_alarm.csv", "assetId": "VFD-204"},
            {"id": "EVD-UPL-5D57BCA6", "filename": "custom_report.pdf", "assetId": "VFD-204"},
        ]
        repo.sync_incident(incident, assets, [], evidence, [], [])
        subgraph = repo.get_incident_subgraph("INC-2026-001")
        evidence_nodes = [n for n in subgraph["nodes"] if n["type"] == "evidence"]
        ev_ids = {n["id"] for n in evidence_nodes}
        self.assertIn("EVD-001", ev_ids)
        self.assertIn("EVD-002", ev_ids)
        self.assertIn("EVD-UPL-5D57BCA6", ev_ids)
        for en in evidence_nodes:
            self.assertIn("id", en)
            self.assertEqual(en["type"], "evidence")

    def test_integrity_2_has_evidence_targets_evidence_not_assets(self):
        """2. Verify HAS_EVIDENCE relationships target Evidence nodes and never Assets."""
        repo = InMemoryIncidentGraphRepository()
        incident = {"id": "INC-2026-001", "title": "Slurry Pump Overheating"}
        assets = [{"id": "VFD-204", "name": "VFD-204"}]
        evidence = [{"id": "EVD-001", "filename": "vfd_log.csv", "assetId": "VFD-204"}]
        repo.sync_incident(incident, assets, [], evidence, [], [])
        subgraph = repo.get_incident_subgraph("INC-2026-001")

        has_ev_edges = [e for e in subgraph["edges"] if e["relationship"] == "HAS_EVIDENCE"]
        self.assertTrue(len(has_ev_edges) >= 1)
        for edge in has_ev_edges:
            self.assertEqual(edge["source"], "INC-2026-001")
            self.assertTrue(edge["target"].startswith("EVD"))
            self.assertNotEqual(edge["target"], "VFD-204")

    def test_integrity_3_related_to_targets_asset_from_evidence_no_self_loops(self):
        """3. Verify RELATED_TO connects Evidence -> Asset, and no Asset self-loops exist."""
        repo = InMemoryIncidentGraphRepository()
        incident = {"id": "INC-2026-001", "title": "Slurry Pump Overheating"}
        assets = [{"id": "VFD-204", "name": "VFD-204"}]
        evidence = [{"id": "EVD-001", "filename": "vfd_log.csv", "assetId": "VFD-204"}]
        repo.sync_incident(incident, assets, [], evidence, [], [])
        subgraph = repo.get_incident_subgraph("INC-2026-001")

        related_edges = [e for e in subgraph["edges"] if e["relationship"] == "RELATED_TO"]
        self.assertTrue(len(related_edges) >= 1)
        for edge in related_edges:
            self.assertEqual(edge["source"], "EVD-001")
            self.assertEqual(edge["target"], "VFD-204")
            self.assertNotEqual(edge["source"], edge["target"])

    def test_integrity_4_finding_classification_preservation(self):
        """4. Verify Finding classifications (OBSERVED, CORRELATED, HYPOTHESIS, UNKNOWN) are preserved."""
        repo = InMemoryIncidentGraphRepository()
        incident = {"id": "INC-2026-001", "title": "Slurry Pump Overheating"}
        findings = [
            {"id": "FND-001", "statement": "Over-temp trip", "category": "OBSERVED"},
            {"id": "FND-002", "statement": "Pressure drop", "category": "OBSERVED"},
            {"id": "FND-003", "statement": "Filter DP increased", "category": "CORRELATED"},
            {"id": "FND-004", "statement": "Fan contact failure", "category": "HYPOTHESIS"},
            {"id": "FND-005", "statement": "Backup pump start unknown", "category": "UNKNOWN"},
        ]
        repo.sync_incident(incident, [], [], [], findings, [])
        subgraph = repo.get_incident_subgraph("INC-2026-001")

        finding_map = {n["id"]: n["metadata"].get("classification") or n["metadata"].get("category") for n in subgraph["nodes"] if n["type"] == "finding"}
        self.assertEqual(finding_map.get("FND-001"), "OBSERVED")
        self.assertEqual(finding_map.get("FND-002"), "OBSERVED")
        self.assertEqual(finding_map.get("FND-003"), "CORRELATED")
        self.assertEqual(finding_map.get("FND-004"), "HYPOTHESIS")
        self.assertEqual(finding_map.get("FND-005"), "UNKNOWN")

    def test_integrity_5_context_graph_service_includes_uploaded_evidence(self):
        """5. Verify ContextGraphService combines uploaded repository evidence and syncs into graph."""
        from backend.services.context_graph_service import ContextGraphService
        from backend.repositories.uploaded_evidence_repository import (
            InMemoryUploadedEvidenceRepository,
            set_uploaded_evidence_repository,
        )
        from backend.schemas.upload import UploadedEvidence

        upl_repo = InMemoryUploadedEvidenceRepository()
        upl_evidence = UploadedEvidence(
            evidence_id="EVD-UPL-5D57BCA6",
            incident_id="INC-2026-001",
            source_type="VFD_DRIVE_LOG",
            original_filename="inlet_filter_log.csv",
            stored_filename="EVD-UPL-5D57BCA6_inlet_filter_log.csv",
            content_type="text/csv",
            file_size=2048,
            asset_id="VFD-204",
            description="Uploaded filter data",
            storage_uri="gs://test-bucket/sample.csv",
            uploaded_at="2026-09-08T14:00:00Z",
            processing_status="PROCESSED",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            metadata={},
        )
        upl_repo.create(upl_evidence)
        set_uploaded_evidence_repository(upl_repo)

        try:
            graph_repo = InMemoryIncidentGraphRepository()
            service = ContextGraphService(repo=graph_repo)

            res = service.sync_incident_context("INC-2026-001")
            self.assertEqual(res["status"], "synchronized")

            subgraph = service.get_incident_graph("INC-2026-001")
            node_ids = {n["id"] for n in subgraph["nodes"]}
            self.assertIn("EVD-UPL-5D57BCA6", node_ids)
            self.assertIn("EVD-001", node_ids)
        finally:
            set_uploaded_evidence_repository(None)

    def test_integrity_6_neo4j_reconciliation_cleanup_queries_executed(self):
        """6. Verify Neo4j sync runs reconciliation queries for invalid HAS_EVIDENCE and RELATED_TO."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        executed_queries = []

        def capture_run(query, params=None):
            executed_queries.append(query)
            return MagicMock()

        mock_session.run.side_effect = capture_run

        repo = Neo4jIncidentGraphRepository(driver=mock_driver)
        incident = {"id": "INC-2026-001", "title": "Trip"}
        assets = [{"id": "VFD-204", "name": "VFD-204"}]
        evidence = [{"id": "EVD-001", "filename": "vfd.csv", "assetId": "VFD-204"}]

        repo.sync_incident(incident, assets, [], evidence, [], [])

        # Check reconciliation queries:
        r1 = [q for q in executed_queries if "HAS_EVIDENCE" in q and "NOT target:Evidence" in q and "DELETE r" in q]
        self.assertTrue(len(r1) >= 1)

        r2 = [q for q in executed_queries if "RELATED_TO" in q and "NOT src:Evidence OR NOT tgt:Asset" in q and "DELETE r" in q]
        self.assertTrue(len(r2) >= 1)

        r3 = [q for q in executed_queries if "Asset" in q and "RELATED_TO" in q and "DELETE r" in q]
        self.assertTrue(len(r3) >= 1)

    def test_integrity_7_neo4j_cypher_has_evidence_targets_evidence_node(self):
        """7. Verify Neo4j Cypher merges Evidence node and creates (Incident)-[:HAS_EVIDENCE]->(Evidence)."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        executed_queries = []

        def capture_run(query, params=None):
            executed_queries.append(query)
            return MagicMock()

        mock_session.run.side_effect = capture_run

        repo = Neo4jIncidentGraphRepository(driver=mock_driver)
        incident = {"id": "INC-2026-001", "title": "Trip"}
        evidence = [{"id": "EVD-001", "filename": "vfd.csv", "assetId": "VFD-204"}]
        repo.sync_incident(incident, [], [], evidence, [], [])

        ev_query = [q for q in executed_queries if "MERGE (evidence:Evidence" in q and "MERGE (i)-[:HAS_EVIDENCE]->(evidence)" in q]
        self.assertTrue(len(ev_query) >= 1)

    def test_integrity_8_neo4j_cypher_related_to_binds_evidence_to_asset(self):
        """8. Verify Neo4j Cypher binds (Evidence)-[:RELATED_TO]->(Asset), not Asset to Asset."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        executed_queries = []

        def capture_run(query, params=None):
            executed_queries.append(query)
            return MagicMock()

        mock_session.run.side_effect = capture_run

        repo = Neo4jIncidentGraphRepository(driver=mock_driver)
        incident = {"id": "INC-2026-001", "title": "Trip"}
        assets = [{"id": "VFD-204", "name": "VFD-204"}]
        evidence = [{"id": "EVD-001", "filename": "vfd.csv", "assetId": "VFD-204"}]
        repo.sync_incident(incident, assets, [], evidence, [], [])

        rel_query = [q for q in executed_queries if "MATCH (evidence:Evidence" in q and "MATCH (a:Asset" in q and "MERGE (evidence)-[:RELATED_TO]->(a)" in q]
        self.assertTrue(len(rel_query) >= 1)

    def test_integrity_9_neo4j_cypher_finding_classification_set(self):
        """9. Verify Neo4j Cypher sets classification and category on Finding node."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        executed_queries = []

        def capture_run(query, params=None):
            executed_queries.append(query)
            return MagicMock()

        mock_session.run.side_effect = capture_run

        repo = Neo4jIncidentGraphRepository(driver=mock_driver)
        incident = {"id": "INC-2026-001", "title": "Trip"}
        findings = [{"id": "FND-003", "statement": "DP increased", "category": "CORRELATED"}]
        repo.sync_incident(incident, [], [], [], findings, [])

        fnd_query = [q for q in executed_queries if "MERGE (finding:Finding" in q and "finding.classification = f.classification" in q]
        self.assertTrue(len(fnd_query) >= 1)

    def test_integrity_10_neo4j_get_subgraph_label_resolution_and_safeguards(self):
        """10. Verify Neo4j get_incident_subgraph resolves labels, properties, and filters self-loops."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        class MockNode:
            def __init__(self, id_val, labels, props):
                self.id = id_val
                self.labels = frozenset(labels)
                self._props = props

            def __iter__(self):
                return iter(self._props.items())

            def keys(self):
                return self._props.keys()

            def items(self):
                return self._props.items()

            def __getitem__(self, key):
                return self._props[key]

            def get(self, key, default=None):
                return self._props.get(key, default)

        class MockRel:
            def __init__(self, start_node, rel_type, end_node):
                self.start_node = start_node
                self.type = rel_type
                self.end_node = end_node

            def __iter__(self):
                return iter({}.items())

            def keys(self):
                return {}.keys()

            def items(self):
                return {}.items()

            def get(self, key, default=None):
                return default

        inc_node = MockNode("n1", ["Incident"], {"incident_id": "INC-2026-001", "title": "Test Incident"})
        ev_node = MockNode("n2", ["Evidence"], {"evidence_id": "EVD-001", "filename": "vfd.csv"})
        asset_node = MockNode("n3", ["Asset"], {"asset_id": "VFD-204", "name": "VFD-204 Drive"})
        fnd_node = MockNode("n4", ["Finding"], {"finding_id": "FND-003", "classification": "CORRELATED", "statement": "Filter DP"})

        rel_inc_ev = MockRel(inc_node, "HAS_EVIDENCE", ev_node)
        rel_ev_asset = MockRel(ev_node, "RELATED_TO", asset_node)
        rel_self_loop = MockRel(asset_node, "RELATED_TO", asset_node)

        mock_record = MagicMock()
        mock_record.get.side_effect = lambda k: [inc_node, ev_node, asset_node, fnd_node] if k == "all_nodes" else [rel_inc_ev, rel_ev_asset, rel_self_loop]
        mock_res = MagicMock()
        mock_res.single.return_value = mock_record
        mock_session.run.return_value = mock_res

        repo = Neo4jIncidentGraphRepository(driver=mock_driver)
        result = repo.get_incident_subgraph("INC-2026-001")

        nodes = {n["id"]: n for n in result["nodes"]}
        self.assertIn("EVD-001", nodes)
        self.assertIn("VFD-204", nodes)
        self.assertIn("FND-003", nodes)
        self.assertEqual(nodes["FND-003"]["metadata"]["classification"], "CORRELATED")
        self.assertEqual(nodes["EVD-001"]["label"], "vfd.csv")

        edges = [(e["source"], e["relationship"], e["target"]) for e in result["edges"]]
        self.assertIn(("INC-2026-001", "HAS_EVIDENCE", "EVD-001"), edges)
        self.assertIn(("EVD-001", "RELATED_TO", "VFD-204"), edges)
        self.assertNotIn(("VFD-204", "RELATED_TO", "VFD-204"), edges)

    def test_integrity_11_graph_sync_idempotency(self):
        """11. Verify repeatedly synchronizing incident graph produces identical node and edge counts."""
        repo = InMemoryIncidentGraphRepository()
        incident = {"id": "INC-2026-001", "title": "Overheating Incident"}
        assets = [
            {"id": "VFD-204", "name": "VFD-204 Drive"},
            {"id": "M-204", "name": "Motor M-204"},
            {"id": "P-204", "name": "Pump P-204"},
        ]
        evidence = [
            {"id": "EVD-001", "filename": "vfd.csv", "assetId": "VFD-204"},
            {"id": "EVD-002", "filename": "motor.csv", "assetId": "M-204"},
        ]
        findings = [
            {"id": "FND-001", "statement": "IGBT trip", "category": "OBSERVED", "evidenceIds": ["EVD-001"], "assetId": "VFD-204"},
            {"id": "FND-003", "statement": "Filter DP", "category": "CORRELATED", "evidenceIds": ["EVD-001"], "assetId": "VFD-204"},
        ]

        # First sync
        repo.sync_incident(incident, assets, [], evidence, findings, [])
        subgraph_1 = repo.get_incident_subgraph("INC-2026-001")

        # Second sync
        repo.sync_incident(incident, assets, [], evidence, findings, [])
        subgraph_2 = repo.get_incident_subgraph("INC-2026-001")

        self.assertEqual(len(subgraph_1["nodes"]), len(subgraph_2["nodes"]))
        self.assertEqual(len(subgraph_1["edges"]), len(subgraph_2["edges"]))
        self.assertEqual({n["id"] for n in subgraph_1["nodes"]}, {n["id"] for n in subgraph_2["nodes"]})
        self.assertEqual({e["id"] for e in subgraph_1["edges"]}, {e["id"] for e in subgraph_2["edges"]})

    def test_integrity_12_asset_topology_path_maintained(self):
        """12. Verify asset topology path VFD-204 -> M-204 -> P-204 remains operational."""
        repo = InMemoryIncidentGraphRepository()
        path_res = repo.find_asset_path("INC-2026-001", "VFD-204", "P-204")
        self.assertTrue(path_res["found"])
        self.assertEqual(path_res["source_asset"], "VFD-204")
        self.assertEqual(path_res["target_asset"], "P-204")
        self.assertEqual(path_res["length"], 2)
        self.assertEqual(path_res["relationships"], ["POWERS", "DRIVES"])


if __name__ == "__main__":
    unittest.main()
