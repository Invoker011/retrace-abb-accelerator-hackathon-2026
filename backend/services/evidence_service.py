"""Evidence Service for retrieving evidence and provenance records."""
from typing import List, Optional
from backend.data.mock_data import MOCK_EVIDENCE
from backend.schemas.evidence import Evidence

class EvidenceService:
    @staticmethod
    def get_all_evidence(incident_id: Optional[str] = None) -> List[Evidence]:
        # Currently all evidence belongs to demo incident INC-2026-001
        return [Evidence(**e) for e in MOCK_EVIDENCE]

    @staticmethod
    def get_evidence_by_id(evidence_id: str) -> Optional[Evidence]:
        for e in MOCK_EVIDENCE:
            if e["id"].upper() == evidence_id.upper():
                return Evidence(**e)
        return None

evidence_service = EvidenceService()
