"""Comprehensive Hardening & Grounding Test Suite for RETRACE.

Verifies:
1. Rejecting "cavitation is the root cause" / causal assertions
2. Rejecting "initiated the chain"
3. Rejecting "mechanical cavitation initiated the chain"
4. Rejecting "electrical surge" (when ungrounded in retrieved evidence)
5. Rejecting "mechanical binding" (when ungrounded in retrieved evidence)
6. Rejecting "NPSHa deficit" / "NPSH deficit"
7. Rejecting "partial blockage, debris, or restriction causing low suction head"
8. Rejecting "Flexible Disc Coupling" (when ungrounded in retrieved evidence)
9. Rejecting "exacerbated torsional vibration under load" / ungrounded torsional vibration
10. Rejecting "cavitation pitting"
11. Rejecting autonomous actuation command (e.g. "reset VFD-204 and restart P-204")
12. Allowing conceptual non-confirmation: "The available evidence does not confirm cavitation as the root cause."
13. Allowing evidence-grounded recorded symptoms (recorded low suction pressure, rattling, vibration, VFD warning)
14. Allowing evidence-grounded inspection guidance: "Inspect P-204 to determine the source of the recorded rattling and baseplate shudder."
15. Single-shot regeneration mechanism: triggers one retry on wording validation failure, succeeds when retry passes.
16. Fail-closed behavior: fails closed when retry also violates grounding.
17. Deterministic InvestigationService.query verification: handles root-cause, actuation, and inspection inquiries strictly grounded.
"""
import json
import unittest
from unittest.mock import MagicMock, patch

from backend.schemas.finding import FindingClassification
from backend.schemas.investigation import (
    InvestigationRequest,
    InvestigationResponse,
    RecommendedCheck,
)
from backend.services.grounded_investigation_service import (
    GroundedInvestigationService,
    InvestigationSafetyError,
    InvestigationValidationError,
    InvestigationWordingValidationError,
    RawGeminiFinding,
    RawGeminiInvestigationOutput,
    RawGeminiRecommendedCheck,
)
from backend.services.hybrid_retrieval_service import HybridRetrievalService
from backend.services.investigation_service import InvestigationService


class TestGroundingHardening(unittest.TestCase):
    def setUp(self):
        self.svc = GroundedInvestigationService()
        self.allowed_ev = {"EVD-001", "EVD-002", "EVD-003", "EVD-006"}
        self.allowed_evt = {"EVT-001", "EVT-002"}
        self.allowed_ast = {"P-204", "VFD-204", "M-204", "PLC-204"}
        self.sample_corpus = (
            "vfd-204 log overcurrent warning w-2310 peak 268.4a inverter stage. "
            "scada alarm log seq #88310 vibration trip interlock execution p-204. "
            "historian p-204 1-second process head flow motor kw trace. "
            "technician observation operator j. miller logged audible gravel-like rattling and baseplate shudder. "
            "suction pressure recorded low suction pressure 0.8 bar. vibration zone c 6.7 mm/s zone d 8.8 mm/s."
        )
        self.retrieval_package = {
            "evidence": [
                {"text": "VFD-204 overcurrent warning W-2310 recorded at 10:14:01.", "filename": "VFD_204_Log.csv"},
                {"text": "Recorded low suction pressure 0.8 bar with gravel-like rattling.", "filename": "Technician_Observation_001.txt"},
            ],
            "events": [],
            "assets": [{"name": "P-204"}, {"name": "VFD-204"}],
        }

    # 1. Rejecting "cavitation is the root cause" / causal assertions
    def test_01_reject_cavitation_as_root_cause(self):
        text = "Cavitation was the root cause of the pump shutdown."
        with self.assertRaises(InvestigationWordingValidationError) as ctx:
            self.svc.validate_copilot_text(text, self.retrieval_package)
        self.assertTrue(
            "prohibited causal assertion" in str(ctx.exception)
            or "unsupported failure mechanism" in str(ctx.exception)
        )

    # 2. Rejecting "initiated the chain"
    def test_02_reject_initiated_the_chain(self):
        text = "An overcurrent event initiated the chain leading to trip."
        with self.assertRaises(InvestigationWordingValidationError) as ctx:
            self.svc.validate_copilot_text(text, self.retrieval_package)
        self.assertIn("initiated the chain", str(ctx.exception))

    # 3. Rejecting "mechanical cavitation initiated the chain"
    def test_03_reject_mechanical_cavitation_initiated_the_chain(self):
        text = "Physical inspection is needed to see if mechanical cavitation initiated the chain."
        with self.assertRaises(InvestigationWordingValidationError) as ctx:
            self.svc.validate_copilot_text(text, self.retrieval_package)
        self.assertTrue(
            "initiated the chain" in str(ctx.exception)
            or "cavitation" in str(ctx.exception)
        )

    # 4. Rejecting "electrical surge" (ungrounded in evidence)
    def test_04_reject_electrical_surge_ungrounded(self):
        text = "The trip was associated with an electrical surge on the inverter."
        with self.assertRaises(InvestigationWordingValidationError) as ctx:
            self.svc.validate_copilot_text(text, self.retrieval_package)
        self.assertIn("electrical surge", str(ctx.exception))

    # 5. Rejecting "mechanical binding" (ungrounded in evidence)
    def test_05_reject_mechanical_binding_ungrounded(self):
        text = "The motor current spike was likely caused by mechanical binding."
        with self.assertRaises(InvestigationWordingValidationError) as ctx:
            self.svc.validate_copilot_text(text, self.retrieval_package)
        self.assertTrue(
            "mechanical binding" in str(ctx.exception)
            or "caused" in str(ctx.exception)
        )

    # 6. Rejecting "NPSHa deficit" / "NPSH deficit"
    def test_06_reject_npsha_deficit(self):
        text = "The pump suffered an NPSHa deficit due to line restriction."
        with self.assertRaises(InvestigationWordingValidationError) as ctx:
            self.svc.validate_copilot_text(text, self.retrieval_package)
        self.assertIn("npsh", str(ctx.exception).lower())

    # 7. Rejecting "partial blockage, debris, or restriction causing low suction head"
    def test_07_reject_blockage_causing_low_suction_head(self):
        text = "Inspect for partial blockage, debris, or restriction causing low suction head."
        with self.assertRaises(InvestigationWordingValidationError) as ctx:
            self.svc.validate_copilot_text(text, self.retrieval_package)
        self.assertTrue(
            "low suction head" in str(ctx.exception).lower()
            or "causing" in str(ctx.exception).lower()
        )

    # 8. Rejecting "Flexible Disc Coupling" (invented component type)
    def test_08_reject_flexible_disc_coupling(self):
        text = "Check the Flexible Disc Coupling for angular misalignment."
        with self.assertRaises(InvestigationWordingValidationError) as ctx:
            self.svc.validate_copilot_text(text, self.retrieval_package)
        self.assertIn("flexible disc coupling", str(ctx.exception).lower())

    # 9. Rejecting "exacerbated torsional vibration under load"
    def test_09_reject_torsional_vibration(self):
        text = "The angular offset exacerbated torsional vibration under load."
        with self.assertRaises(InvestigationWordingValidationError) as ctx:
            self.svc.validate_copilot_text(text, self.retrieval_package)
        self.assertTrue(
            "torsional vibration" in str(ctx.exception).lower()
            or "prohibited causal assertion" in str(ctx.exception).lower()
        )

    # 10. Rejecting "cavitation pitting"
    def test_10_reject_cavitation_pitting(self):
        text = "Disassemble casing and inspect for cavitation pitting on the impeller vanes."
        with self.assertRaises(InvestigationWordingValidationError) as ctx:
            self.svc.validate_copilot_text(text, self.retrieval_package)
        self.assertIn("cavitation", str(ctx.exception).lower())

    # 11. Rejecting autonomous actuation commands (Advisory Safety)
    def test_11_reject_actuation_command(self):
        text = "Reset VFD-204 and restart Pump P-204 to clear the trip state."
        with self.assertRaises(InvestigationSafetyError) as ctx:
            self.svc.validate_copilot_text(text, self.retrieval_package)
        self.assertIn("prohibited equipment actuation command", str(ctx.exception).lower())

    # 12. Allowing conceptual non-confirmation of cavitation
    def test_12_allow_cavitation_non_confirmation(self):
        text = (
            "The available evidence does not confirm cavitation as the root cause. "
            "Recorded evidence documents recorded low suction pressure and rising vibration."
        )
        # Must NOT raise InvestigationWordingValidationError
        self.svc.validate_copilot_text(text, self.retrieval_package)

    # 13. Allowing evidence-grounded recorded symptoms
    def test_13_allow_grounded_recorded_symptoms(self):
        text = (
            "Recorded evidence documents: recorded low suction pressure (0.8 bar), "
            "audible gravel-like rattling and baseplate shudder at 10:14:18, rising vibration "
            "entering Zone C (6.7 mm/s) and Zone D (8.8 mm/s), VFD-204 overcurrent warning "
            "W-2310 at 10:14:01, and PLC-204 shutdown alarm at 10:14:28. The available evidence "
            "does not establish an unverified mechanical root cause."
        )
        self.svc.validate_copilot_text(text, self.retrieval_package)

    # 14. Allowing evidence-grounded inspection guidance
    def test_14_allow_grounded_inspection_guidance(self):
        check = RecommendedCheck(
            check="Inspect P-204 to determine the source of the recorded rattling and baseplate shudder.",
            reason="Investigate physical condition following documented audible shudder.",
            related_asset_ids=["P-204"],
        )
        validated = self.svc.validate_recommended_check(
            check,
            allowed_asset_ids={"P-204"},
            retrieved_corpus=self.sample_corpus,
        )
        self.assertEqual(validated.check, "Inspect P-204 to determine the source of the recorded rattling and baseplate shudder.")

    # 15. Single-shot regeneration mechanism succeeds when retry passes
    def test_15_single_shot_regeneration_success(self):
        mock_client = MagicMock()
        mock_hybrid = MagicMock(spec=HybridRetrievalService)

        retrieval_result = {
            "incident_id": "INC-2026-001",
            "query": "Why did P-204 trip?",
            "top_k": 5,
            "evidence": [
                {
                    "rank": 1,
                    "evidence_id": "EVD-001",
                    "asset_id": "VFD-204",
                    "filename": "VFD_204_Log.csv",
                    "source_type": "VFD / Drive Logs",
                    "text": "VFD-204 overcurrent warning W-2310 recorded at 10:14:01.",
                    "provenance": {"source": "VFD_204_Log.csv"},
                }
            ],
            "events": [],
            "assets": [{"name": "VFD-204"}, {"name": "P-204"}],
            "temporal_context": [],
            "recognized_identifiers": ["VFD-204", "P-204"],
        }
        mock_hybrid.search_hybrid.return_value = retrieval_result

        # First attempt contains ungrounded "mechanical binding"
        first_bad_output = {
            "summary": "VFD-204 overcurrent preceded shutdown.",
            "findings": [
                {
                    "classification": "HYPOTHESIS",
                    "statement": "Mechanical binding may have triggered the spike.",
                    "basis": "Inferred from EVD-001 overcurrent warning.",
                    "evidence_ids": ["EVD-001"],
                    "event_ids": [],
                    "asset_ids": ["VFD-204"],
                }
            ],
            "unknowns": ["Upstream condition remains unknown."],
            "recommended_checks": [
                {
                    "check": "Inspect VFD-204 fault records.",
                    "reason": "Verify inverter conditions.",
                    "related_asset_ids": ["VFD-204"],
                }
            ],
        }

        # Second attempt (regenerated) adheres to grounded rules
        second_good_output = {
            "summary": "VFD-204 overcurrent preceded shutdown.",
            "findings": [
                {
                    "classification": "HYPOTHESIS",
                    "statement": "An abnormal electrical load may have preceded the spike.",
                    "basis": "Inferred from EVD-001 overcurrent warning.",
                    "evidence_ids": ["EVD-001"],
                    "event_ids": [],
                    "asset_ids": ["VFD-204"],
                }
            ],
            "unknowns": ["Upstream condition remains unknown."],
            "recommended_checks": [
                {
                    "check": "Inspect VFD-204 fault records.",
                    "reason": "Verify inverter conditions.",
                    "related_asset_ids": ["VFD-204"],
                }
            ],
        }

        resp_first = MagicMock()
        resp_first.text = json.dumps(first_bad_output)
        resp_second = MagicMock()
        resp_second.text = json.dumps(second_good_output)

        mock_client.models.generate_content.side_effect = [resp_first, resp_second]

        svc = GroundedInvestigationService(hybrid_retrieval_service=mock_hybrid, client=mock_client)
        req = InvestigationRequest(query="Why did P-204 trip?", top_k=5)
        res = svc.investigate("INC-2026-001", req)

        self.assertIsInstance(res, InvestigationResponse)
        self.assertEqual(len(res.findings), 1)
        self.assertEqual(res.findings[0].statement, "An abnormal electrical load may have preceded the spike.")
        # Ensure model was invoked exactly twice (1 original + 1 regeneration)
        self.assertEqual(mock_client.models.generate_content.call_count, 2)

    # 16. Fail-closed: when retry also violates grounding, raises exception
    def test_16_fail_closed_when_regeneration_fails(self):
        mock_client = MagicMock()
        mock_hybrid = MagicMock(spec=HybridRetrievalService)

        retrieval_result = {
            "incident_id": "INC-2026-001",
            "query": "Why did P-204 trip?",
            "top_k": 5,
            "evidence": [
                {
                    "rank": 1,
                    "evidence_id": "EVD-001",
                    "asset_id": "VFD-204",
                    "filename": "VFD_204_Log.csv",
                    "source_type": "VFD / Drive Logs",
                    "text": "VFD-204 overcurrent warning W-2310 recorded at 10:14:01.",
                    "provenance": {"source": "VFD_204_Log.csv"},
                }
            ],
            "events": [],
            "assets": [{"name": "VFD-204"}, {"name": "P-204"}],
            "temporal_context": [],
            "recognized_identifiers": ["VFD-204", "P-204"],
        }
        mock_hybrid.search_hybrid.return_value = retrieval_result

        bad_output = {
            "summary": "VFD-204 overcurrent caused the shutdown.",  # Prohibited causal assertion
            "findings": [
                {
                    "classification": "OBSERVED",
                    "statement": "VFD-204 overcurrent occurred.",
                    "basis": "Documented in EVD-001.",
                    "evidence_ids": ["EVD-001"],
                    "event_ids": [],
                    "asset_ids": ["VFD-204"],
                }
            ],
            "unknowns": [],
            "recommended_checks": [],
        }

        resp_first = MagicMock()
        resp_first.text = json.dumps(bad_output)
        resp_second = MagicMock()
        resp_second.text = json.dumps(bad_output)

        mock_client.models.generate_content.side_effect = [resp_first, resp_second]

        svc = GroundedInvestigationService(hybrid_retrieval_service=mock_hybrid, client=mock_client)
        req = InvestigationRequest(query="Why did P-204 trip?", top_k=5)

        with self.assertRaises(InvestigationWordingValidationError):
            svc.investigate("INC-2026-001", req)

        self.assertEqual(mock_client.models.generate_content.call_count, 2)

    # 17. Deterministic InvestigationService.query verification
    def test_17_investigation_service_deterministic_grounding(self):
        # Root cause question
        resp1 = InvestigationService.query("INC-2026-001", "Was cavitation the root cause?")
        self.assertIn("evidence does not confirm cavitation", resp1.answer.lower())
        self.assertNotIn("npsha deficit", resp1.answer.lower())
        self.assertNotIn("flexible disc coupling", resp1.answer.lower())
        self.assertNotIn("cavitation pitting", resp1.answer.lower())

        # Actuation question
        resp2 = InvestigationService.query("INC-2026-001", "Should I reset VFD-204 and restart P-204 now?")
        self.assertIn("advisory only", resp2.answer.lower())
        self.assertIn("do not reset", resp2.answer.lower())
        self.assertIn("loto", resp2.answer.lower())

        # Inspection question
        resp3 = InvestigationService.query("INC-2026-001", "What should the technician inspect next?")
        self.assertNotIn("npsha deficit", resp3.answer.lower())
        self.assertNotIn("flexible disc coupling", resp3.answer.lower())
        self.assertNotIn("cavitation pitting", resp3.answer.lower())
        self.assertNotIn("mechanical binding", resp3.answer.lower())
        self.assertIn("advisory only", resp3.answer.lower())


if __name__ == "__main__":
    unittest.main()
