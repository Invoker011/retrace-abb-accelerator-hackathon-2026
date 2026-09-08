"""Deterministic Mock Investigation Service for RETRACE.
Grounds query responses in synthetic multi-modal evidence without LLM generation at this stage.
Preserves strict industrial distinction between OBSERVED, CORRELATED, HYPOTHESIS, and UNKNOWN.
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
            "What triggered the initial 480ms overcurrent pulse in VFD-204?",
            "Was the cavitation triggered by upstream suction line blockage or sudden impeller loading?",
            "Did the +0.08mm angular coupling offset noted in WO-88492 aggravate high-frequency vibration under load?",
        ]
        suggested_follow_ups = [
            "What happened before the shutdown?",
            "Which assets were involved?",
            "What evidence supports this finding?",
            "What should the technician inspect next?",
            "What information is still missing?",
        ]

        if "why did pump p-204 shut down" in q or "why did it shut down" in q or "cause of shutdown" in q:
            classification = FindingClassification.CORRELATED
            supporting_ids = ["EVD-001", "EVD-002", "EVD-003"]
            answer = (
                "The available evidence shows that VFD-204 recorded an overcurrent warning 27 seconds "
                "before the PLC shutdown alarm. Motor M-204 current deviation and Pump P-204 process "
                "disturbance followed. These events are temporally correlated across physically related "
                "assets, but the available evidence does not confirm the exact mechanical root cause."
            )
            unresolved_questions = [
                "What caused the instantaneous overcurrent peak in VFD-204 at 10:14:01?",
                "Was there physical mechanical binding in pump P-204 or an upstream electrical surge?",
                "What was the suction strainer differential pressure prior to cavitation onset?",
            ]

        elif "before the shutdown" in q or "happened before" in q:
            classification = FindingClassification.OBSERVED
            supporting_ids = ["EVD-001", "EVD-003"]
            answer = (
                "Sequence reconstructed from drive logs and historian:\n\n"
                "1. 10:14:01 — VFD-204 recorded an overcurrent warning (268.4A peak) at the inverter output stage.\n"
                "2. 10:14:05 — Motor M-204 experienced an 8.2% phase current imbalance.\n"
                "3. 10:14:12 — Pump P-204 discharge pressure dropped precipitously from 6.8 bar to 4.2 bar.\n"
                "4. 10:14:18 — Operator J. Miller logged audible cavitation screech and baseplate vibration.\n\n"
                "All early warning milestones occurred within a 27-second window before the trip alarm."
            )
            unresolved_questions = [
                "Why was the drive warning W-2310 not configured to alert the main DCS console?",
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
                "1. Suction Strainer ST-204: Inspect for partial blockage, debris, or restriction causing low suction head (NPSHa deficit).\n"
                "2. Flexible Disc Coupling: Verify whether the +0.08mm angular offset reported in WO-88492 exacerbated torsional vibration under load.\n"
                "3. Pump Impeller & Casing: Inspect for cavitation pitting or mechanical binding.\n\n"
                "⚠️ Safety Notice: RETRACE is advisory only. Ensure Lock-Out / Tag-Out (LOTO) protocols are executed prior to physical intervention."
            )
            unresolved_questions = [
                "Has permit-to-work for cold mechanical teardown of Skid B been authorized?",
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
                "• Technician_Observation_001: Independent human operator confirmation of audible screech and baseplate shaking at 10:14:18."
            )

        else:
            classification = FindingClassification.CORRELATED
            supporting_ids = ["EVD-001", "EVD-003", "EVD-002"]
            answer = (
                f"Based on ingested evidence for {incident_id}, VFD-204 registered an overcurrent warning "
                "at 10:14:01, followed by Motor M-204 current divergence, Pump P-204 pressure drop, and "
                "PLC-204 trip at 10:14:28. The temporal and physical correlation across assets is established, "
                "but physical inspection is required to determine whether an electrical surge or mechanical cavitation "
                "initiated the chain."
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

        return InvestigationQueryResponse(
            answer=answer,
            findings=relevant_findings,
            supporting_evidence=supporting_evidence_data,
            classification=classification,
            unresolved_questions=unresolved_questions,
            suggested_follow_ups=suggested_follow_ups,
        )

investigation_service = InvestigationService()
