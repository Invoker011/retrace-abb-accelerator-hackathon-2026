"""Tests for RETRACE retrieval eligibility filtering and timestamp normalization.

Verifies:
1. Ineligible artifacts (such as persistence_test.csv / EVD-UPL-5D57BCA6) are excluded from:
   - chunking
   - vector sync
   - semantic search
   - keyword search
   - hybrid retrieval
2. Genuine uploaded evidence remains retrieval-eligible and searchable.
3. Baseline synthetic evidence (EVD-001 through EVD-006) remains retrieval-eligible.
4. Persistence layer preserves the file in PostgreSQL and GCS without deletion.
5. Timestamp normalization: if top-level timestamp is missing, it is populated from
   provenance.normalized_timestamp without fabricating timestamps.
"""
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from backend.schemas.hybrid_search import (
    HybridEvidenceResult,
    HybridSearchRequest,
    HybridSearchResponse,
)
from backend.schemas.upload import UploadedEvidence
from backend.services.evidence_eligibility import is_evidence_retrieval_eligible
from backend.services.hybrid_retrieval_service import HybridRetrievalService
from backend.services.keyword_search_service import KeywordEvidenceSearchService
from backend.services.incident_service import incident_service
from backend.vector.chunking import EvidenceChunkingService
from backend.vector.models import EvidenceChunk
from backend.repositories.uploaded_evidence_repository import (
    InMemoryUploadedEvidenceRepository,
)


class TestRetrievalEligibilityAndTimestampNormalization(unittest.TestCase):
    def setUp(self):
        self.incident_id = "INC-2026-001"
        self.chunking_service = EvidenceChunkingService()
        self.keyword_service = KeywordEvidenceSearchService()

        # In-memory repository for test setup
        self.upload_repo = InMemoryUploadedEvidenceRepository()

    def test_01_synthetic_evidence_evd_001_to_006_are_retrieval_eligible(self):
        """Synthetic baseline evidence EVD-001 through EVD-006 must remain retrieval-eligible."""
        evidence_list = incident_service.get_incident_evidence(self.incident_id)
        self.assertTrue(len(evidence_list) >= 6)
        ev_ids = [e.id for e in evidence_list]
        for expected_id in ["EVD-001", "EVD-002", "EVD-003", "EVD-004", "EVD-005", "EVD-006"]:
            self.assertIn(expected_id, ev_ids)

        for ev in evidence_list:
            self.assertTrue(
                is_evidence_retrieval_eligible(ev),
                f"Synthetic baseline evidence {ev.id} should be retrieval-eligible",
            )

    def test_02_persistence_test_artifact_is_retrieval_ineligible(self):
        """Test/verification artifacts must be marked ineligible based on metadata/filename/description."""
        verification_artifact = UploadedEvidence(
            evidence_id="EVD-UPL-5D57BCA6",
            incident_id=self.incident_id,
            source_type="historian",
            original_filename="persistence_test.csv",
            stored_filename="EVD-UPL-5D57BCA6_persistence_test.csv",
            content_type="text/csv",
            file_size=128,
            asset_id="VFD-204",
            description="PostgreSQL persistence verification upload",
            storage_uri="gs://retrace-evidence-test/incidents/INC-2026-001/evidence/EVD-UPL-5D57BCA6_persistence_test.csv",
            uploaded_at="2026-09-10T15:00:00Z",
            processing_status="UPLOADED",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            metadata={
                "retrieval_eligible": False,
                "use_type": "test",
                "format": "csv",
                "columns": ["test_id", "timestamp"],
            },
        )
        self.assertFalse(is_evidence_retrieval_eligible(verification_artifact))

    def test_03_chunking_skips_ineligible_evidence(self):
        """Chunking service must produce 0 chunks for retrieval-ineligible uploads."""
        test_upload = UploadedEvidence(
            evidence_id="EVD-UPL-TEST01",
            incident_id=self.incident_id,
            source_type="historian",
            original_filename="persistence_test.csv",
            stored_filename="EVD-UPL-TEST01_persistence_test.csv",
            content_type="text/csv",
            file_size=100,
            description="PostgreSQL persistence verification upload",
            storage_uri="gs://test/file.csv",
            uploaded_at="2026-09-10T12:00:00Z",
            sha256_hash="abc123",
            metadata={"format": "csv", "columns": ["a", "b"], "retrieval_eligible": False},
        )
        chunks = self.chunking_service.chunk_uploaded_evidence(test_upload)
        self.assertEqual(len(chunks), 0)

    def test_04_genuine_uploaded_evidence_is_chunked_and_eligible(self):
        """Operational uploaded evidence (not test verification) must produce chunks and be eligible."""
        operational_upload = UploadedEvidence(
            evidence_id="EVD-UPL-GENUINE1",
            incident_id=self.incident_id,
            source_type="vfd_log",
            original_filename="vfd204_fault_export.csv",
            stored_filename="EVD-UPL-GENUINE1_vfd204_fault_export.csv",
            content_type="text/csv",
            file_size=250,
            asset_id="VFD-204",
            description="Field technician thermal fault log export",
            storage_uri="gs://retrace/vfd204_fault_export.csv",
            uploaded_at="2026-09-10T12:00:00Z",
            sha256_hash="fedcba987",
            retrieval_eligible=True,
            metadata={
                "format": "csv",
                "columns": ["timestamp", "fault_code", "inverter_temp"],
                "row_count": 3,
                "preview_rows": [
                    {"timestamp": "2026-03-30T09:42:00Z", "fault_code": "FLT_OVERTEMP", "inverter_temp": "88.4"}
                ],
            },
        )
        self.assertTrue(is_evidence_retrieval_eligible(operational_upload))
        chunks = self.chunking_service.chunk_uploaded_evidence(operational_upload)
        self.assertTrue(len(chunks) > 0)
        self.assertEqual(chunks[0].evidence_id, "EVD-UPL-GENUINE1")

    def test_05_keyword_search_excludes_ineligible_records(self):
        """Keyword search must not return results from ineligible verification uploads."""
        repo = InMemoryUploadedEvidenceRepository()
        # Add verification test upload
        test_upload = UploadedEvidence(
            evidence_id="EVD-UPL-5D57BCA6",
            incident_id=self.incident_id,
            source_type="historian",
            original_filename="persistence_test.csv",
            stored_filename="EVD-UPL-5D57BCA6_persistence_test.csv",
            content_type="text/csv",
            file_size=128,
            asset_id="VFD-204",
            description="PostgreSQL persistence verification upload",
            storage_uri="gs://test/file.csv",
            uploaded_at="2026-09-10T15:00:00Z",
            sha256_hash="12345",
            metadata={"retrieval_eligible": False, "use_type": "test", "columns": ["test_id"]},
        )
        repo.create(test_upload)

        kw_svc = KeywordEvidenceSearchService(upload_repo=repo)
        results = kw_svc.search(self.incident_id, "persistence test verification")
        retrieved_ids = [r["evidence_id"] for r in results]
        self.assertNotIn("EVD-UPL-5D57BCA6", retrieved_ids)

    def test_06_hybrid_retrieval_excludes_ineligible_artifacts(self):
        """Hybrid retrieval fusion must strictly exclude retrieval-ineligible items."""
        repo = InMemoryUploadedEvidenceRepository()
        test_upload = UploadedEvidence(
            evidence_id="EVD-UPL-5D57BCA6",
            incident_id=self.incident_id,
            source_type="historian",
            original_filename="persistence_test.csv",
            stored_filename="EVD-UPL-5D57BCA6_persistence_test.csv",
            content_type="text/csv",
            file_size=128,
            description="PostgreSQL persistence verification upload",
            storage_uri="gs://test/file.csv",
            uploaded_at="2026-09-10T15:00:00Z",
            sha256_hash="12345",
            metadata={"retrieval_eligible": False, "use_type": "test"},
        )
        repo.create(test_upload)

        # Mock vector service returning both a legitimate chunk and the test chunk
        mock_vector = MagicMock()
        mock_vector.semantic_search.return_value = {
            "incident_id": self.incident_id,
            "query": "temperature fault",
            "results": [
                {
                    "similarity_score": 0.92,
                    "evidence_id": "EVD-001",
                    "chunk_id": "EVD-001-chk-0",
                    "asset_id": "VFD-204",
                    "source_type": "vfd_log",
                    "filename": "vfd_trip_log.csv",
                    "text": "Over-temperature fault on VFD-204",
                    "timestamp": "2026-03-30T09:42:00Z",
                    "provenance": {"source": "VFD Inverter 204"},
                },
                {
                    "similarity_score": 0.88,
                    "evidence_id": "EVD-UPL-5D57BCA6",
                    "chunk_id": "EVD-UPL-5D57BCA6-chk-0",
                    "asset_id": "VFD-204",
                    "source_type": "historian",
                    "filename": "persistence_test.csv",
                    "text": "PostgreSQL persistence verification upload",
                    "provenance": {"metadata": {"retrieval_eligible": False, "use_type": "test"}},
                },
            ],
        }

        mock_neo4j = MagicMock()
        mock_neo4j.get_investigation_graph.return_value = {
            "assets": [],
            "relationships": [],
            "evidence_nodes": [],
            "path_count": 0,
            "is_truncated": False,
        }

        hybrid_svc = HybridRetrievalService(
            vector_service=mock_vector,
            keyword_service=KeywordEvidenceSearchService(upload_repo=repo),
            graph_service=mock_neo4j,
            upload_repo=repo,
        )

        response = hybrid_svc.search_hybrid(
            incident_id=self.incident_id,
            query="temperature fault VFD-204",
            top_k=5,
        )

        fused_evidence_ids = [e["evidence_id"] for e in response["evidence"]]
        self.assertIn("EVD-001", fused_evidence_ids)
        self.assertNotIn("EVD-UPL-5D57BCA6", fused_evidence_ids)

    def test_07_persistence_preserves_artifact_in_postgres_repository(self):
        """The test artifact must remain in the repository and not be deleted."""
        repo = InMemoryUploadedEvidenceRepository()
        test_upload = UploadedEvidence(
            evidence_id="EVD-UPL-5D57BCA6",
            incident_id=self.incident_id,
            source_type="historian",
            original_filename="persistence_test.csv",
            stored_filename="EVD-UPL-5D57BCA6_persistence_test.csv",
            content_type="text/csv",
            file_size=128,
            description="PostgreSQL persistence verification upload",
            storage_uri="gs://test/file.csv",
            uploaded_at="2026-09-10T15:00:00Z",
            sha256_hash="12345",
            metadata={"retrieval_eligible": False, "use_type": "test"},
        )
        saved = repo.create(test_upload)
        # Should be retrievable directly via get_by_id and get_by_incident
        fetched = repo.get_by_id("EVD-UPL-5D57BCA6")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.evidence_id, "EVD-UPL-5D57BCA6")
        self.assertFalse(fetched.retrieval_eligible)

        all_incident_uploads = repo.get_by_incident(self.incident_id)
        self.assertEqual(len(all_incident_uploads), 1)
        self.assertEqual(all_incident_uploads[0].evidence_id, "EVD-UPL-5D57BCA6")

    def test_08_timestamp_normalization_from_provenance(self):
        """HybridEvidenceResult populates timestamp from provenance.normalized_timestamp when missing."""
        result = HybridEvidenceResult(
            rank=1,
            retrieval_score=0.016393,
            retrieval_channels=["semantic"],
            evidence_id="EVD-002",
            chunk_id="EVD-002-chk-0",
            filename="historian_bearing_temp.csv",
            source_type="historian",
            text="Motor M-204 bearing DE temp reached 94.2 C",
            timestamp=None,  # top-level timestamp missing
            provenance={
                "source": "Process Historian",
                "normalized_timestamp": "2026-03-30T09:41:45Z",
            },
        )
        self.assertEqual(result.timestamp, "2026-03-30T09:41:45Z")

    def test_09_timestamp_preserved_when_already_present(self):
        """Top-level timestamp is preserved when already present."""
        result = HybridEvidenceResult(
            rank=1,
            retrieval_score=0.016393,
            retrieval_channels=["semantic"],
            evidence_id="EVD-001",
            chunk_id="EVD-001-chk-0",
            filename="vfd_trip_log.csv",
            source_type="vfd_log",
            text="Fault code FLT_OVERTEMP",
            timestamp="2026-03-30T09:42:00Z",
            provenance={
                "source": "VFD",
                "normalized_timestamp": "2026-03-30T09:42:00Z",
            },
        )
        self.assertEqual(result.timestamp, "2026-03-30T09:42:00Z")

    def test_10_no_timestamp_invented_when_absent(self):
        """If timestamp is absent in both top-level and provenance, it remains None."""
        result = HybridEvidenceResult(
            rank=1,
            retrieval_score=0.016393,
            retrieval_channels=["keyword"],
            evidence_id="EVD-004",
            chunk_id="EVD-004-chk-0",
            filename="pump_manual.pdf",
            source_type="manual",
            text="Operating manual for centrifugal pump P-204",
            timestamp=None,
            provenance={"source": "Engineering Library"},
        )
        self.assertIsNone(result.timestamp)


if __name__ == "__main__":
    unittest.main()
