"""Deterministic Industrial Identifier Recognition for RETRACE.

Identifies explicit industrial operational and equipment identifiers from user
queries without invoking LLM reasoning, adhering to deterministic pattern matching.
"""
import re
from typing import Dict, List, Set

# Compiled regex with strict word boundaries to avoid false positives
IDENTIFIER_PATTERN = re.compile(
    r"\b("
    r"INC-\d{4}-\d{3,4}"              # Incident identifiers (e.g. INC-2026-001)
    r"|(?:VFD|M|P|PLC)-\d{2,4}"       # Asset tags (e.g. VFD-204, M-204, P-204, PLC-204)
    r"|EVD-UPL-[A-Fa-f0-9]+"          # Uploaded evidence identifiers (e.g. EVD-UPL-5D57BCA6)
    r"|EVD-\d{3,4}"                   # Baseline evidence identifiers (e.g. EVD-001)
    r"|EVT-\d{3,4}"                   # Timeline event identifiers (e.g. EVT-001)
    r"|FND-\d{3,4}"                   # Finding identifiers (e.g. FND-001)
    r"|WO-\d{4,6}"                    # CMMS work order tags (e.g. WO-88492)
    r"|ALM-[A-Za-z0-9\-]+"            # SCADA alarm IDs (e.g. ALM-P204-TRIP-VIB)
    r"|W-\d{4}"                       # Inverter/drive warning codes (e.g. W-2310)
    r")\b",
    re.IGNORECASE,
)

ASSET_PATTERN = re.compile(r"^(?:VFD|M|P|PLC)-\d{2,4}$", re.IGNORECASE)
EVIDENCE_PATTERN = re.compile(r"^(?:EVD-\d{3,4}|EVD-UPL-[A-Fa-f0-9]+)$", re.IGNORECASE)
EVENT_PATTERN = re.compile(r"^EVT-\d{3,4}$", re.IGNORECASE)
INCIDENT_PATTERN = re.compile(r"^INC-\d{4}-\d{3,4}$", re.IGNORECASE)
FINDING_PATTERN = re.compile(r"^FND-\d{3,4}$", re.IGNORECASE)


class IdentifierRecognitionService:
    """Service for deterministic extraction of RETRACE identifiers."""

    @staticmethod
    def extract_identifiers(query: str) -> List[str]:
        """Extract all recognized RETRACE identifiers from the query string.

        Guarantees:
        - Deterministic extraction via strict regular expressions
        - Zero false positives on partial tags (e.g., 'P-', 'VFD', 'EVT')
        - Canonical uppercase normalization
        - Deduplication while preserving order of first appearance
        """
        if not query or not isinstance(query, str):
            return []

        raw_matches = IDENTIFIER_PATTERN.findall(query)
        seen: Set[str] = set()
        normalized: List[str] = []

        for match in raw_matches:
            canonical = match.upper().strip()
            if canonical and canonical not in seen:
                seen.add(canonical)
                normalized.append(canonical)

        return normalized

    @staticmethod
    def categorize_identifiers(identifiers: List[str]) -> Dict[str, List[str]]:
        """Categorize extracted identifiers into asset, evidence, event, incident, finding, and other."""
        categorized: Dict[str, List[str]] = {
            "assets": [],
            "evidence": [],
            "events": [],
            "incidents": [],
            "findings": [],
            "alarms_and_workorders": [],
        }

        for ident in identifiers:
            upper = ident.upper()
            if ASSET_PATTERN.match(upper):
                categorized["assets"].append(upper)
            elif EVIDENCE_PATTERN.match(upper):
                categorized["evidence"].append(upper)
            elif EVENT_PATTERN.match(upper):
                categorized["events"].append(upper)
            elif INCIDENT_PATTERN.match(upper):
                categorized["incidents"].append(upper)
            elif FINDING_PATTERN.match(upper):
                categorized["findings"].append(upper)
            else:
                categorized["alarms_and_workorders"].append(upper)

        return categorized

    @staticmethod
    def is_asset_tag(ident: str) -> bool:
        """Check if an identifier is an equipment asset tag."""
        return bool(ASSET_PATTERN.match(ident))

    @staticmethod
    def is_evidence_id(ident: str) -> bool:
        """Check if an identifier is an evidence identifier."""
        return bool(EVIDENCE_PATTERN.match(ident))


# Global singleton instance
identifier_recognition_service = IdentifierRecognitionService()
