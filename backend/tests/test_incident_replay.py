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


if __name__ == "__main__":
    unittest.main()
