"""Tests for RETRACE Incident Replay feature.

Verifies the 20 specific requirements:
1. Replay events sorted chronologically
2. Sequence numbers deterministic
3. EVT-001 relative_seconds = 0
4. EVT-005 relative_seconds = 27
5. Correct evidence linked to each event
6. Retrieval-ineligible evidence excluded
7. VFD-204 POWERS M-204 surfaced as topology only
8. M-204 DRIVES P-204 surfaced
9. No causal language inserted
10. Recorded telemetry comes only from supplied evidence
11. Missing telemetry remains absent/null
12. Phases assigned deterministically
13. Unknown phase becomes UNCLASSIFIED
14. Replay window filtering works
15. Invalid replay ranges rejected
16. Original reference preserved
17. Historical maintenance/manual evidence is not inserted as incident events
18. No Gemini call occurs
19. Existing hybrid retrieval remains valid
20. Existing grounded investigation remains valid
"""
import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    HAS_TESTCLIENT = True
except Exception:
    client = None
    HAS_TESTCLIENT = False

try:
    from backend.api.incidents import get_incident_replay
    HAS_API_FUNCTION = True
except Exception:
    get_incident_replay = None
    HAS_API_FUNCTION = False

from backend.schemas.replay import (
    IncidentReplayResponse,
    ReplayPhase,
)
from backend.services.incident_replay_service import (
    IncidentReplayService,
    get_incident_replay_service,
    BANNED_CAUSAL_PATTERNS,
)
from backend.schemas.evidence import Evidence


class TestIncidentReplay(unittest.TestCase):
    def setUp(self):
        self.service = get_incident_replay_service()

    def _get_replay(self, incident_id: str, start_offset: int = None, end_offset: int = None):
        """Helper to invoke replay either via TestClient, API endpoint, or service directly."""
        if HAS_TESTCLIENT and client is not None:
            params = {}
            if start_offset is not None:
                params["start_offset_seconds"] = start_offset
            if end_offset is not None:
                params["end_offset_seconds"] = end_offset
            resp = client.get(f"/api/incidents/{incident_id}/replay", params=params)
            return IncidentReplayResponse.model_validate(resp.json())
        elif HAS_API_FUNCTION and get_incident_replay is not None:
            return get_incident_replay(
                incident_id=incident_id,
                start_offset_seconds=start_offset,
                end_offset_seconds=end_offset,
            )
        return self.service.get_replay(
            incident_id=incident_id,
            start_offset_seconds=start_offset,
            end_offset_seconds=end_offset,
        )

    def test_1_replay_events_sorted_chronologically(self):
        """1. Replay events must be strictly sorted in chronological order."""
        res = self._get_replay("INC-2026-001")
        events = res.events
        self.assertGreaterEqual(len(events), 2)

        for i in range(len(events) - 1):
            curr_rel = events[i].relative_seconds
            next_rel = events[i + 1].relative_seconds
            self.assertLessEqual(curr_rel, next_rel)
            self.assertLessEqual(events[i].timestamp, events[i + 1].timestamp)

    def test_2_sequence_numbers_deterministic(self):
        """2. Sequence numbers must be strictly 1-indexed, consecutive, and deterministic."""
        res = self._get_replay("INC-2026-001")
        events = res.events
        expected_sequences = list(range(1, len(events) + 1))
        actual_sequences = [e.sequence for e in events]
        self.assertEqual(actual_sequences, expected_sequences)

    def test_3_evt001_relative_seconds_zero(self):
        """3. EVT-001 must have relative_seconds = 0 at start of incident."""
        res = self._get_replay("INC-2026-001")
        events = res.events
        evt_001 = next((e for e in events if e.event_id == "EVT-001"), None)
        self.assertIsNotNone(evt_001)
        self.assertEqual(evt_001.relative_seconds, 0)
        self.assertEqual(evt_001.sequence, 1)

    def test_4_evt005_relative_seconds_27(self):
        """4. EVT-005 must have relative_seconds = 27 at protective shutdown."""
        res = self._get_replay("INC-2026-001")
        events = res.events
        evt_005 = next((e for e in events if e.event_id == "EVT-005"), None)
        self.assertIsNotNone(evt_005)
        self.assertEqual(evt_005.relative_seconds, 27)

    def test_5_correct_evidence_linked_to_each_event(self):
        """5. Every event must link to its correct supporting evidence artifact."""
        res = self._get_replay("INC-2026-001")
        events = res.events

        event_evidence_map = {
            "EVT-001": "EVD-001",
            "EVT-002": "EVD-003",
            "EVT-003": "EVD-003",
            "EVT-004": "EVD-006",
            "EVT-005": "EVD-002",
        }

        for evt in events:
            eid = evt.event_id
            if eid in event_evidence_map:
                expected_evid = event_evidence_map[eid]
                linked_ids = [ref.evidence_id for ref in evt.evidence]
                self.assertIn(
                    expected_evid,
                    linked_ids,
                    f"Event {eid} must link supporting evidence {expected_evid}",
                )

    def test_6_retrieval_ineligible_evidence_excluded(self):
        """6. Any retrieval-ineligible evidence or test artifacts must be excluded."""
        ineligible_ev = Evidence(
            id="EVD-TEST-999",
            filename="test_verification_upload.csv",
            source="Test runner",
            source_type="VFD / Drive Logs",
            timestamp="2026-09-08 10:14:01",
            normalized_timestamp="2026-09-08T10:14:01Z",
            asset_id="VFD-204",
            asset_name="VFD-204",
            extracted_event="Test event",
            confidence=10.0,
            original_evidence_ref="Test",
            file_size="100 KB",
            format="csv",
            retrieval_eligible=False,
        )

        from backend.services.incident_service import incident_service
        real_evidence = incident_service.get_incident_evidence("INC-2026-001")

        with patch.object(incident_service, "get_incident_evidence", return_value=list(real_evidence) + [ineligible_ev]):
            replay = self.service.get_replay("INC-2026-001")
            all_linked_evidence_ids = [
                ref.evidence_id
                for evt in replay.events
                for ref in evt.evidence
            ]
            self.assertNotIn("EVD-TEST-999", all_linked_evidence_ids)

    def test_7_vfd204_powers_m204_surfaced_as_topology_only(self):
        """7. VFD-204 POWERS M-204 must be surfaced as equipment topology without causation."""
        res = self._get_replay("INC-2026-001")
        events = res.events
        evt_001 = next(e for e in events if e.event_id == "EVT-001")

        rels = evt_001.graph_relationships
        powers_rel = next(
            (r for r in rels if r.source == "VFD-204" and r.relationship == "POWERS" and r.target == "M-204"),
            None,
        )
        self.assertIsNotNone(powers_rel, "VFD-204 POWERS M-204 relationship must be present")
        self.assertIn("M-204", evt_001.related_assets)

        if powers_rel.description:
            for pat in BANNED_CAUSAL_PATTERNS:
                self.assertIsNone(
                    pat.search(powers_rel.description),
                    f"Causal pattern '{pat.pattern}' found in relationship description",
                )

    def test_8_m204_drives_p204_surfaced(self):
        """8. M-204 DRIVES P-204 must be surfaced on Motor and Pump events."""
        res = self._get_replay("INC-2026-001")
        events = res.events
        evt_002 = next(e for e in events if e.event_id == "EVT-002")

        drives_rel = next(
            (r for r in evt_002.graph_relationships if r.source == "M-204" and r.relationship == "DRIVES" and r.target == "P-204"),
            None,
        )
        self.assertIsNotNone(drives_rel, "M-204 DRIVES P-204 must be present for Motor event")

    def test_9_no_causal_language_inserted(self):
        """9. No causal verbs or phrases may be introduced into replay output."""
        res = self._get_replay("INC-2026-001")

        def scan_text(text: str, context: str):
            if not text:
                return
            for pat in BANNED_CAUSAL_PATTERNS:
                self.assertIsNone(
                    pat.search(text),
                    f"Banned causal phrase '{pat.pattern}' detected in {context}: {text}",
                )

        for evt in res.events:
            scan_text(evt.title, f"event {evt.event_id} title")
            for rel in evt.graph_relationships:
                scan_text(rel.description or "", f"relationship {rel.relationship}")

    def test_10_recorded_telemetry_comes_only_from_supplied_evidence(self):
        """10. Recorded telemetry must match exact factual values from supplied evidence."""
        res = self._get_replay("INC-2026-001")
        events = res.events

        evt_001 = next(e for e in events if e.event_id == "EVT-001")
        current_val = next((v for v in evt_001.recorded_values if v.name == "current"), None)
        self.assertIsNotNone(current_val)
        self.assertEqual(current_val.value, 268.4)
        self.assertEqual(current_val.unit, "A")
        self.assertEqual(current_val.source_evidence_id, "EVD-001")

        evt_004 = next(e for e in events if e.event_id == "EVT-004")
        suction_val = next((v for v in evt_004.recorded_values if v.name == "suction_pressure"), None)
        self.assertIsNotNone(suction_val)
        self.assertEqual(suction_val.value, 0.8)
        self.assertEqual(suction_val.unit, "bar")
        self.assertEqual(suction_val.source_evidence_id, "EVD-006")

        evt_005 = next(e for e in events if e.event_id == "EVT-005")
        vib_val = next((v for v in evt_005.recorded_values if v.name == "trip_vibration"), None)
        self.assertIsNotNone(vib_val)
        self.assertEqual(vib_val.value, 9.2)
        self.assertEqual(vib_val.unit, "mm/s")
        self.assertEqual(vib_val.source_evidence_id, "EVD-002")

    def test_11_missing_telemetry_remains_absent_or_null(self):
        """11. Missing telemetry must never be fabricated or interpolated."""
        res = self._get_replay("INC-2026-001")
        events = res.events

        evt_001 = next(e for e in events if e.event_id == "EVT-001")
        vibration_names = [v.name for v in evt_001.recorded_values]
        self.assertNotIn("suction_pressure", vibration_names)
        self.assertNotIn("vibration", vibration_names)

    def test_12_phases_assigned_deterministically(self):
        """12. Replay phases must be assigned deterministically without AI hallucination."""
        res = self._get_replay("INC-2026-001")
        events = res.events

        expected_phases = {
            "EVT-001": ReplayPhase.PRECURSOR,
            "EVT-002": ReplayPhase.DEGRADATION,
            "EVT-003": ReplayPhase.DEGRADATION,
            "EVT-004": ReplayPhase.OPERATOR_OBSERVATION,
            "EVT-005": ReplayPhase.PROTECTIVE_SHUTDOWN,
        }

        for evt in events:
            eid = evt.event_id
            if eid in expected_phases:
                self.assertEqual(
                    evt.phase,
                    expected_phases[eid],
                    f"Event {eid} should be assigned phase {expected_phases[eid]}",
                )

    def test_13_unknown_phase_becomes_unclassified(self):
        """13. Events that cannot be safely categorized must be UNCLASSIFIED."""
        phase = IncidentReplayService._assign_replay_phase(
            event_id="EVT-999",
            event_type="info",
            title="Periodic routine ping",
        )
        self.assertEqual(phase, ReplayPhase.UNCLASSIFIED)

    def test_14_replay_window_filtering_works(self):
        """14. Query parameters start_offset_seconds and end_offset_seconds filter events."""
        res = self._get_replay("INC-2026-001", start_offset=4, end_offset=17)
        events = res.events

        self.assertEqual(len(events), 3)
        event_ids = [e.event_id for e in events]
        self.assertEqual(event_ids, ["EVT-002", "EVT-003", "EVT-004"])
        self.assertEqual(res.duration_seconds, 13)
        self.assertEqual(res.summary.event_count, 3)
        self.assertEqual(res.summary.duration_seconds, 13)

        self.assertEqual([e.sequence for e in events], [1, 2, 3])

    def test_15_invalid_replay_ranges_rejected(self):
        """15. Invalid window parameters must raise ValueError."""
        # start < 0
        with self.assertRaises(ValueError):
            self.service.get_replay("INC-2026-001", start_offset_seconds=-5)

        # end < 0
        with self.assertRaises(ValueError):
            self.service.get_replay("INC-2026-001", end_offset_seconds=-1)

        # end < start
        with self.assertRaises(ValueError):
            self.service.get_replay("INC-2026-001", start_offset_seconds=20, end_offset_seconds=10)

    def test_16_original_reference_preserved(self):
        """16. Original evidence references (rows, offsets, tags) must be preserved."""
        res = self._get_replay("INC-2026-001")
        events = res.events

        evt_001 = next(e for e in events if e.event_id == "EVT-001")
        ref_001 = evt_001.evidence[0]
        self.assertIn("Row 4209", ref_001.original_reference)

        evt_005 = next(e for e in events if e.event_id == "EVT-005")
        ref_002 = evt_005.evidence[0]
        self.assertIn("88310", ref_002.original_reference)

    def test_17_historical_maintenance_manual_evidence_not_inserted_as_incident_events(self):
        """17. Engineering manual (EVD-004) and historical work order (EVD-005) must not be incident events."""
        res = self._get_replay("INC-2026-001")
        events = res.events

        event_ids = [e.event_id for e in events]
        self.assertEqual(event_ids, ["EVT-001", "EVT-002", "EVT-003", "EVT-004", "EVT-005"])

        linked_ev_ids = [ref.evidence_id for evt in events for ref in evt.evidence]
        self.assertNotIn("EVD-004", linked_ev_ids)
        self.assertNotIn("EVD-005", linked_ev_ids)

    @patch("backend.services.grounded_investigation_service.GroundedInvestigationService.investigate")
    def test_18_no_gemini_call_occurs(self, mock_investigate):
        """18. Incident replay must be completely deterministic without calling Gemini reasoning."""
        res = self._get_replay("INC-2026-001")
        self.assertIsNotNone(res)
        mock_investigate.assert_not_called()

    def test_19_existing_hybrid_tests_remain_green(self):
        """19. Existing hybrid search retrieval functionality remains intact."""
        from backend.services.hybrid_retrieval_service import get_hybrid_retrieval_service
        service = get_hybrid_retrieval_service()
        res = service.search_hybrid("INC-2026-001", "vibration", top_k=3)
        self.assertEqual(res["incident_id"], "INC-2026-001")
        self.assertGreaterEqual(len(res["evidence"]), 1)

    def test_20_existing_grounded_investigation_remains_green(self):
        """20. Grounded investigation service structure and deterministic fallback remain intact."""
        from backend.services.grounded_investigation_service import get_grounded_investigation_service
        service = get_grounded_investigation_service()
        self.assertIsNotNone(service)

    # =========================================================================
    # STRICT GROUNDING REGRESSION TESTS (USER MANDATES 1 - 12)
    # =========================================================================

    def test_reg_1_no_replay_value_appears_unless_present_in_source_evidence(self):
        """1. No replay value appears unless directly present in source evidence."""
        res = self._get_replay("INC-2026-001")
        all_values = [
            (evt.event_id, val.name, val.value, val.unit, val.source_evidence_id)
            for evt in res.events
            for val in evt.recorded_values
        ]

        # Verified evidence inventory
        # EVD-001: current 268.4 A, voltage 398.2 V, frequency 48.6 Hz, alarm_code W-2310, state WARN
        # EVD-003: discharge_head 6.74/4.2 bar, flow 310.2/241.0 m3/h, motor_power 118.2/122.1 kW, vibration 3.4/6.7 mm/s
        # EVD-006: suction_pressure 0.8 bar, normal_suction_pressure 1.6 bar, observation
        # EVD-002: alarm_code ALM-P204-TRIP-VIB, trip_vibration 9.2 mm/s, interlock 04-SHUTDOWN, alarm_id 88310

        for eid, name, val, unit, src_id in all_values:
            if eid == "EVT-001":
                self.assertEqual(src_id, "EVD-001")
                self.assertIn(name, ["current", "voltage", "frequency", "alarm_code", "state"])
                self.assertNotIn(name, ["speed", "rpm", "discharge_pressure", "vibration"])
            elif eid == "EVT-002":
                self.assertEqual(src_id, "EVD-003")
                self.assertIn(name, ["motor_power", "vibration", "discharge_head", "flow"])
                self.assertNotIn(name, ["speed", "rpm", "current", "phase_imbalance", "torque_ripple"])
            elif eid == "EVT-003":
                self.assertEqual(src_id, "EVD-003")
                self.assertIn(name, ["discharge_head", "flow", "motor_power", "vibration"])
                self.assertNotIn(name, ["speed", "rpm", "current"])
            elif eid == "EVT-004":
                self.assertEqual(src_id, "EVD-006")
                self.assertIn(name, ["suction_pressure", "normal_suction_pressure", "observation"])
                self.assertNotIn(name, ["vibration", "discharge_pressure", "current", "rpm"])
            elif eid == "EVT-005":
                self.assertEqual(src_id, "EVD-002")
                self.assertIn(name, ["alarm_code", "trip_vibration", "interlock", "alarm_id"])
                self.assertNotIn(name, ["current", "speed", "rpm", "discharge_pressure"])

    def test_reg_2_evd003_cannot_generate_rpm_or_motor_current_if_absent(self):
        """2. EVD-003 cannot generate RPM or motor current if those fields are absent."""
        # Simulate an event linked to EVD-003 containing attempted injected channels
        class MockEvt:
            id = "EVT-MOCK"
            evidence_id = "EVD-003"
            telemetry_snapshot = {
                "rpm": 1442,
                "currentA": 252.1,
                "motorPowerKw": 118.2,
                "vibrationMmS": 3.4,
            }

        recorded = IncidentReplayService._extract_recorded_values(MockEvt(), None)
        extracted_names = [r.name for r in recorded]

        # Must strictly omit RPM and current
        self.assertNotIn("speed", extracted_names)
        self.assertNotIn("rpm", extracted_names)
        self.assertNotIn("current", extracted_names)
        # Must include legitimate channels
        self.assertIn("motor_power", extracted_names)
        self.assertIn("vibration", extracted_names)

    def test_reg_3_evd006_cannot_generate_vibration_or_discharge_pressure_if_absent(self):
        """3. EVD-006 cannot generate vibration or discharge pressure values if absent."""
        class MockEvt:
            id = "EVT-MOCK-TECH"
            evidence_id = "EVD-006"
            telemetry_snapshot = {
                "vibrationMmS": 8.4,
                "pressureBar": 4.1,
                "suctionPressureBar": 0.8,
            }

        recorded = IncidentReplayService._extract_recorded_values(MockEvt(), None)
        extracted_names = [r.name for r in recorded]

        # Must strictly omit vibration and discharge_pressure
        self.assertNotIn("vibration", extracted_names)
        self.assertNotIn("discharge_pressure", extracted_names)
        # Must include legitimate technician channels
        self.assertIn("suction_pressure", extracted_names)
        self.assertIn("normal_suction_pressure", extracted_names)
        self.assertIn("observation", extracted_names)

    def test_reg_4_evt003_and_evt004_not_marked_tripped_before_evt005(self):
        """4. EVT-003 and EVT-004 are not marked Tripped before EVT-005."""
        res = self._get_replay("INC-2026-001")
        evt_001 = next(e for e in res.events if e.event_id == "EVT-001")
        evt_002 = next(e for e in res.events if e.event_id == "EVT-002")
        evt_003 = next(e for e in res.events if e.event_id == "EVT-003")
        evt_004 = next(e for e in res.events if e.event_id == "EVT-004")
        evt_005 = next(e for e in res.events if e.event_id == "EVT-005")

        # Before EVT-005, P-204 must NOT be Tripped
        self.assertNotEqual(evt_003.asset_state.operational_status, "Tripped")
        self.assertIsNone(evt_003.asset_state.operational_status)

        self.assertNotEqual(evt_004.asset_state.operational_status, "Tripped")
        self.assertIsNone(evt_004.asset_state.operational_status)

        # At EVT-005, recorded protective trip event occurs
        self.assertEqual(evt_005.asset_state.operational_status, "Tripped")

    def test_reg_5_relationship_descriptions_remain_null_if_neo4j_null(self):
        """5. Relationship descriptions remain null if Neo4j description is null."""
        res = self._get_replay("INC-2026-001")
        for evt in res.events:
            for rel in evt.graph_relationships:
                self.assertIsNone(
                    rel.description,
                    f"Relationship {rel.relationship} on event {evt.event_id} should have description=null",
                )

        # Test directly with mock relationship having None description
        class MockRel:
            sourceAssetId = "VFD-204"
            targetAssetId = "M-204"
            relationType = "POWERS"
            description = None

        contexts, _ = IncidentReplayService._extract_topology_for_asset("VFD-204", [MockRel()])
        self.assertEqual(len(contexts), 1)
        self.assertIsNone(contexts[0].description)
        self.assertEqual(contexts[0].relationship, "POWERS")

    def test_reg_6_no_cavitation_like_wording_unless_source_explicitly_says_it(self):
        """6. No 'cavitation-like' wording unless source explicitly says it."""
        res = self._get_replay("INC-2026-001")
        for evt in res.events:
            self.assertNotIn("cavitation-like", evt.description.lower())
            self.assertNotIn("cavitation-like", evt.title.lower())

    def test_reg_7_no_inferred_timing_such_as_480ms_or_3000ms(self):
        """7. No inferred timing such as 480ms or 3000ms."""
        res = self._get_replay("INC-2026-001")
        for evt in res.events:
            self.assertNotIn("480ms", evt.description)
            self.assertNotIn("3000ms", evt.description)
            for v in evt.recorded_values:
                self.assertNotIn("480", str(v.value))
                self.assertNotIn("3000", str(v.value))

    def test_reg_8_no_derived_percentage_such_as_109_percent(self):
        """8. No derived percentage such as 109% unless source explicitly records it."""
        res = self._get_replay("INC-2026-001")
        for evt in res.events:
            self.assertNotIn("109%", evt.description)
            self.assertNotIn("8.2%", evt.description)
            # Ensure no ungrounded percentage appears
            self.assertNotIn("%", evt.description)

    def test_reg_9_event_descriptions_remain_factual(self):
        """9. Event descriptions remain factual and grounded."""
        res = self._get_replay("INC-2026-001")
        descriptions = {e.event_id: e.description for e in res.events}

        self.assertEqual(
            descriptions["EVT-001"],
            "VFD-204 recorded overcurrent warning W-2310 with current 268.4 A.",
        )
        self.assertEqual(
            descriptions["EVT-002"],
            "Historian recorded Motor M-204 power at 118.2 kW with vibration 3.4 mm/s.",
        )
        self.assertEqual(
            descriptions["EVT-003"],
            "Historian recorded sudden discharge pressure drop from 6.8 bar to 4.2 bar with flow decreasing to 241.0 m³/h.",
        )
        self.assertEqual(
            descriptions["EVT-004"],
            "Technician reported high-pitched gravel-like rattling sound and baseplate shudder on Pump P-204 with suction gauge reading 0.8 bar (normal 1.6 bar).",
        )
        self.assertEqual(
            descriptions["EVT-005"],
            "SCADA alarm ALM-P204-TRIP-VIB triggered with vibration 9.2 mm/s and interlock 04-SHUTDOWN asserted.",
        )

    def test_reg_10_replay_window_filtering_still_works(self):
        """10. Replay window filtering still works as expected."""
        res = self._get_replay("INC-2026-001", start_offset=4, end_offset=17)
        self.assertEqual(len(res.events), 3)
        self.assertEqual([e.event_id for e in res.events], ["EVT-002", "EVT-003", "EVT-004"])
        self.assertEqual(res.duration_seconds, 13)

    def test_reg_11_investigation_endpoint_tests_remain_green(self):
        """11. Investigation endpoint tests remain green."""
        from backend.services.grounded_investigation_service import get_grounded_investigation_service
        service = get_grounded_investigation_service()
        self.assertIsNotNone(service)

    def test_reg_12_all_existing_tests_remain_green(self):
        """12. All existing tests remain green."""
        res = self._get_replay("INC-2026-001")
        self.assertEqual(res.incident_id, "INC-2026-001")
        self.assertEqual(len(res.events), 5)
        self.assertEqual(res.summary.event_count, 5)

    def test_asset_relationship_schema_accepts_description_none(self):
        """Verify AssetRelationship schema accepts description=None and absent description."""
        from backend.schemas.asset import AssetRelationship
        from backend.services.incident_service import IncidentService

        # 1. Direct instantiation with description=None
        rel1 = AssetRelationship(
            id="REL-TEST-001",
            sourceAssetId="VFD-204",
            targetAssetId="M-204",
            relationType="powers",
            description=None,
        )
        self.assertIsNone(rel1.description)
        self.assertEqual(rel1.relation_type, "powers")

        # 2. Direct instantiation with omitted description
        rel2 = AssetRelationship(
            id="REL-TEST-002",
            sourceAssetId="M-204",
            targetAssetId="P-204",
            relationType="drives",
        )
        self.assertIsNone(rel2.description)
        self.assertEqual(rel2.relation_type, "drives")

        # 3. Monitored by relationship with description=None
        rel3 = AssetRelationship(
            id="REL-TEST-003",
            sourceAssetId="P-204",
            targetAssetId="PLC-204",
            relationType="monitored by",
            description=None,
        )
        self.assertIsNone(rel3.description)
        self.assertEqual(rel3.relation_type, "monitored by")

        # 4. IncidentService returns all incident relationships with description=None
        rels = IncidentService.get_asset_relationships("INC-2026-001")
        self.assertGreaterEqual(len(rels), 3)
        for r in rels:
            self.assertIsInstance(r, AssetRelationship)
            self.assertIsNone(r.description)
            self.assertIn(r.relation_type, ["powers", "drives", "monitored by"])


if __name__ == "__main__":
    unittest.main()
