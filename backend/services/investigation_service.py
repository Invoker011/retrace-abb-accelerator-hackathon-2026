"""Deterministic Investigation Service for RETRACE.
Grounds query responses in multi-modal evidence with strict industrial grounding.
Preserves strict industrial distinction between OBSERVED, CORRELATED, HYPOTHESIS, and UNKNOWN.
Enforces advisory safety and rejects ungrounded textbook theories and unproven causal assertions.
"""
from typing import Any, Dict, List
from backend.data.mock_data import MOCK_EVIDENCE, MOCK_FINDINGS
from backend.schemas.finding import Finding, FindingClassification
from backend.schemas.investigation import InvestigationQueryResponse

class InvestigationService:
    @staticmethod
    def query(incident_id: str, question: str) -> InvestigationQueryResponse:
        q = question.strip().lower()

        # Default fallback values
        classification = FindingClassification.CORRELATED
        supporting_ids = ["EVD-001", "EVD-003", "EVD-002"]
        unresolved_questions = [
            "What was recorded prior to the initial overcurrent warning in VFD-204 at 10:14:01?",
            "What was the recorded suction pressure prior to the protective shutdown?",
            "What did physical inspection of pump P-204 internal casing and impeller determine?",
        ]
        suggested_follow_ups = [
            "What happened before the shutdown?",
            "Which assets were involved?",
            "What evidence supports this finding?",
            "What should the technician inspect next?",
            "What information is still missing?",
        ]

        # 1. Direct root-cause inquiry (e.g. "Was cavitation the root cause?")
        if (
            "was cavitation" in q
            or "is cavitation" in q
            or ("cavitation" in q and ("root cause" in q or "cause of" in q or "caused" in q))
        ):
            classification = FindingClassification.CORRELATED
            supporting_ids = ["EVD-001", "EVD-002", "EVD-003", "EVD-006"]
            answer = (
                "The available evidence does not confirm cavitation as the root cause. "
                "Recorded evidence documents: recorded low suction pressure (0.8 bar), "
                "audible gravel-like rattling and baseplate shudder at 10:14:18, rising vibration "
                "entering Zone C (6.7 mm/s) and Zone D (8.8 mm/s), VFD-204 overcurrent warning "
                "W-2310 at 10:14:01, and PLC-204 shutdown alarm at 10:14:28. The available evidence "
                "does not prove cavitation or establish an unverified mechanical root cause."
            )
            unresolved_questions = [
                "What was the suction-pressure trend prior to the 0.8 bar reading at 10:14:18?",
                "What did physical inspection of pump P-204 internal casing and impeller determine?",
            ]

        # 2. Advisory safety / actuation inquiry (e.g. "Should I reset VFD-204 and restart P-204 now?")
        elif (
            "reset" in q
            or "restart" in q
            or "start pump" in q
            or "clear lockout" in q
            or "restart p-204" in q
            or "reset vfd" in q
        ):
            classification = FindingClassification.CORRELATED
            supporting_ids = ["EVD-001", "EVD-002"]
            answer = (
                "RETRACE is advisory only and cannot provide direct machinery restart or fault reset instructions. "
                "Do not reset VFD-204 or restart Pump P-204 without following site-approved Lock-Out/Tag-Out (LOTO) "
                "procedures, completing required mechanical and electrical inspections, and obtaining authorization "
                "from qualified engineering personnel."
            )
            unresolved_questions = [
                "Have mechanical, electrical, and suction-side inspection checks been completed and signed off?",
                "Has qualified engineering review authorized equipment re-energization?",
            ]

        elif "why did pump p-204 shut down" in q or "why did it shut down" in q or "cause of shutdown" in q:
            classification = FindingClassification.CORRELATED
            supporting_ids = ["EVD-001", "EVD-002", "EVD-003"]
            answer = (
                "The available evidence shows that VFD-204 recorded an overcurrent warning 27 seconds "
                "before the PLC shutdown alarm. Motor M-204 current deviation and Pump P-204 process "
                "disturbance followed. These events are temporally correlated across physically related "
                "assets, but the available evidence does not confirm the exact mechanical root cause."
            )
            unresolved_questions = [
                "What was recorded before the instantaneous overcurrent peak in VFD-204 at 10:14:01?",
                "What was the recorded suction pressure prior to the pump protective shutdown?",
                "What did physical inspection of pump P-204 internal casing and impeller determine?",
            ]

        elif "before the shutdown" in q or "happened before" in q:
            classification = FindingClassification.OBSERVED
            supporting_ids = ["EVD-001", "EVD-003", "EVD-006"]
            answer = (
                "Sequence reconstructed from drive logs, historian, and technician records:\n\n"
                "1. 10:14:01 — VFD-204 recorded an overcurrent warning (268.4A peak) at the inverter output stage.\n"
                "2. 10:14:05 — Motor M-204 experienced an 8.2% phase current imbalance.\n"
                "3. 10:14:12 — Pump P-204 discharge pressure dropped from 6.8 bar to 4.2 bar.\n"
                "4. 10:14:18 — Operator J. Miller logged audible gravel-like rattling and baseplate shudder.\n\n"
                "All early warning milestones occurred within a 27-second window before the trip alarm."
            )
            unresolved_questions = [
                "Why was the drive warning W-2310 not configured to alert the central SCADA console?",
            ]

        elif "which assets" in q or "assets were involved" in q:
            classification = FindingClassification.CORRELATED
            supporting_ids = ["EVD-001", "EVD-002", "EVD-003"]
            answer = (
                "Four key assets are in the direct mechanical and electrical power train:\n\n"
                "• VFD-204 (Variable Frequency Drive): powers Motor M-204.\n"
                "• Motor M-204 (110kW Induction Motor): drives Pump P-204.\n"
                "• Pump P-204 (Centrifugal Booster Pump): monitored by PLC-204.\n"
                "• PLC-204 (Safety & Process Controller): executed the hard trip interlock."
            )

        elif "inspect next" in q or "what should the technician inspect" in q or "technician inspect" in q:
            classification = FindingClassification.HYPOTHESIS
            supporting_ids = ["EVD-004", "EVD-005", "EVD-006"]
            answer = (
                "Recommended Human Engineering & Physical Inspection Steps:\n\n"
                "1. Inspect P-204 to determine the source of the recorded rattling and baseplate shudder.\n"
                "2. Review available VFD-204 warning/fault records associated with W-2310.\n"
                "3. Review suction-pressure history and available suction-side inspection records.\n"
                "4. Verify whether the documented M-204 alignment recheck was completed.\n\n"
                "⚠️ Safety Notice: RETRACE is advisory only. Ensure Lock-Out / Tag-Out (LOTO) protocols are executed prior to physical intervention."
            )
            unresolved_questions = [
                "Has permit-to-work for cold mechanical inspection of Skid B been authorized?",
            ]

        elif "missing" in q or "information is still missing" in q:
            classification = FindingClassification.UNKNOWN
            supporting_ids = []
            answer = (
                "Current Evidence Gaps (Unknown):\n\n"
                "• High-frequency spectral FFT vibration data during the 10:14:01 overcurrent pulse is currently missing (historian recorded 1-second RMS averages only).\n"
                "• Physical condition of the pump impeller and suction basket has not yet been visually confirmed.\n"
                "• Drive DC bus ripple voltage telemetry during the initial 480ms spike has not been downloaded from inverter internal trace."
            )
            unresolved_questions = [
                "Can the high-speed drive buffer trace (0x3F8A) be dumped to an engineering workstation?",
                "Is physical suction basket inspection scheduled for the next shift?",
            ]

        elif "evidence supports" in q or "what evidence" in q:
            classification = FindingClassification.OBSERVED
            supporting_ids = ["EVD-001", "EVD-002", "EVD-003", "EVD-006"]
            answer = (
                "The investigation findings are grounded in multi-modal evidence artifacts:\n\n"
                "• VFD_204_Log.csv: Hardware-stamped overcurrent warning W-2310 (Row 4209).\n"
                "• SCADA_Alarm_Log.csv: Alarm Seq #88310 vibration trip interlock execution.\n"
                "• Historian_P204.csv: Synchronized 1-second process head/flow/motor kW trace.\n"
                "• Technician_Observation_001: Independent human operator confirmation of audible gravel-like rattling and baseplate shudder at 10:14:18."
            )

        else:
            classification = FindingClassification.CORRELATED
            supporting_ids = ["EVD-001", "EVD-003", "EVD-002"]
            answer = (
                f"Based on ingested evidence for {incident_id}, VFD-204 registered an overcurrent warning "
                "at 10:14:01, which was recorded before Motor M-204 current deviation, Pump P-204 pressure drop, and "
                "PLC-204 trip at 10:14:28. The chronological sequence across assets is established, "
                "but the exact cause is not established by the available evidence."
            )

        # Collect matching findings
        relevant_findings = [
            Finding(**f)
            for f in MOCK_FINDINGS
            if f.get("incidentId", "").upper() == incident_id.upper()
        ]

        # Collect supporting evidence summaries
        supporting_evidence_data: List[Dict[str, Any]] = []
        for e in MOCK_EVIDENCE:
            if e["id"] in supporting_ids:
                supporting_evidence_data.append({
                    "id": e["id"],
                    "filename": e["filename"],
                    "sourceType": e["sourceType"],
                    "source_type": e["source_type"],
                    "summary": e["extractedEvent"],
                    "confidence": e["confidence"],
                    "originalReference": e["original_reference"],
                })

        # Deterministic Copilot Validation Check (fail-closed if answer violates grounding or safety)
        from backend.services.grounded_investigation_service import get_grounded_investigation_service
        grounded_svc = get_grounded_investigation_service()
        mock_retrieval_package = {
            "evidence": [{"text": e.get("extracted_content") or e.get("extractedEvent", ""), "filename": e.get("filename", "")} for e in MOCK_EVIDENCE if e["id"] in supporting_ids],
            "events": [],
            "assets": [],
        }
        grounded_svc.validate_copilot_text(answer, retrieval_result=mock_retrieval_package, field_name="Copilot answer")

        return InvestigationQueryResponse(
            answer=answer,
            findings=relevant_findings,
            supporting_evidence=supporting_evidence_data,
            classification=classification,
            unresolved_questions=unresolved_questions,
            suggested_follow_ups=suggested_follow_ups,
        )

investigation_service = InvestigationService()
