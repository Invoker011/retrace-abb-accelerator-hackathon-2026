"""Unit tests for evidence repository layer and persistence lifecycle."""
import os
import unittest
from unittest.mock import MagicMock, patch

from backend.schemas.upload import UploadedEvidence
from backend.repositories.uploaded_evidence_repository import (
    InMemoryUploadedEvidenceRepository,
    ProductionUnconfiguredRepository,
    get_uploaded_evidence_repository,
    set_uploaded_evidence_repository,
)
from backend.services.upload_service import IngestionService, IngestionError
from backend.database.session import check_database_health


class TestUploadedEvidenceRepository(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryUploadedEvidenceRepository()
        set_uploaded_evidence_repository(self.repo)
        self.service = IngestionService(repo=self.repo)

    def tearDown(self):
        set_uploaded_evidence_repository(None)

    def _sample_record(self, evidence_id="EVD-UPL-001", incident_id="INC-2026-001", sha="abcdef0123456789"*4):
        return UploadedEvidence(
            evidence_id=evidence_id,
            incident_id=incident_id,
            source_type="VFD_DRIVE_LOG",
            original_filename="vfd_telemetry.csv",
            stored_filename=f"{evidence_id}_vfd_telemetry.csv",
            content_type="text/csv",
            file_size=1024,
            asset_id="VFD-204",
            description="VFD current surge sample",
            storage_uri=f"gs://test-bucket/incidents/{incident_id}/evidence/{evidence_id}_vfd_telemetry.csv",
            uploaded_at="2026-09-08T12:00:00+00:00",
            processing_status="UPLOADED",
            sha256_hash=sha,
            metadata={"format": "csv", "row_count": 50},
        )

    def test_repository_create_and_get_by_id(self):
        """Verify repository creates record and retrieves by ID."""
        rec = self._sample_record("EVD-UPL-101")
        self.repo.create(rec)
        retrieved = self.repo.get_by_id("EVD-UPL-101")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.evidence_id, "EVD-UPL-101")
        self.assertEqual(retrieved.asset_id, "VFD-204")
        self.assertEqual(retrieved.file_size, 1024)

    def test_repository_get_by_incident(self):
        """Verify repository filters uploads by incident_id."""
        rec1 = self._sample_record("EVD-UPL-201", incident_id="INC-2026-001")
        rec2 = self._sample_record("EVD-UPL-202", incident_id="INC-2026-001")
        rec3 = self._sample_record("EVD-UPL-203", incident_id="INC-2026-999")
        self.repo.create(rec1)
        self.repo.create(rec2)
        self.repo.create(rec3)

        inc_records = self.repo.get_by_incident("INC-2026-001")
        self.assertEqual(len(inc_records), 2)
        ids = {r.evidence_id for r in inc_records}
        self.assertEqual(ids, {"EVD-UPL-201", "EVD-UPL-202"})

    def test_repository_delete(self):
        """Verify repository deletes record and subsequent lookup returns None."""
        rec = self._sample_record("EVD-UPL-301")
        self.repo.create(rec)
        self.assertTrue(self.repo.delete("EVD-UPL-301"))
        self.assertIsNone(self.repo.get_by_id("EVD-UPL-301"))
        self.assertFalse(self.repo.delete("EVD-UPL-NONEXISTENT"))

    def test_repository_find_by_hash(self):
        """Verify finding records matching specific SHA-256 hash."""
        test_hash = "1234567890abcdef" * 4
        rec1 = self._sample_record("EVD-UPL-401", sha=test_hash)
        rec2 = self._sample_record("EVD-UPL-402", sha="different_hash_000" * 3 + "0000000")
        self.repo.create(rec1)
        self.repo.create(rec2)

        matches = self.repo.find_by_hash(test_hash)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].evidence_id, "EVD-UPL-401")

    def test_persistence_survives_service_recreation(self):
        """Verify uploaded evidence metadata survives new IngestionService instances when repository persists."""
        rec = self._sample_record("EVD-UPL-501")
        self.repo.create(rec)

        # Create a new service instance sharing the same repository
        new_service = IngestionService(repo=self.repo)
        item = new_service.get_upload_by_id("EVD-UPL-501")
        self.assertIsNotNone(item)
        self.assertEqual(item.evidence_id, "EVD-UPL-501")

    def test_delete_flow_cleans_storage_and_metadata(self):
        """Verify delete_upload removes both raw file via storage service and metadata via repository."""
        rec = self._sample_record("EVD-UPL-601")
        self.repo.create(rec)

        with patch("backend.services.upload_service.evidence_storage.delete_file") as mock_delete_storage:
            mock_delete_storage.return_value = True
            result = self.service.delete_upload("EVD-UPL-601")
            self.assertTrue(result)
            mock_delete_storage.assert_called_once_with(
                incident_id="INC-2026-001",
                evidence_id="EVD-UPL-601",
                filename="EVD-UPL-601_vfd_telemetry.csv",
            )
            self.assertIsNone(self.repo.get_by_id("EVD-UPL-601"))

    def test_consistency_rollback_on_db_failure(self):
        """Verify that if database metadata insertion fails, the newly uploaded storage file is deleted."""
        failing_repo = MagicMock()
        failing_repo.create.side_effect = Exception("Database connection lost")
        service = IngestionService(repo=failing_repo)

        with patch("backend.services.upload_service.evidence_storage.save_file", return_value="gs://bucket/file.csv"):
            with patch("backend.services.upload_service.evidence_storage.delete_file") as mock_delete_storage:
                with self.assertRaises(IngestionError) as ctx:
                    service.upload_evidence(
                        incident_id="INC-2026-001",
                        original_filename="sample.csv",
                        content_type="text/csv",
                        file_bytes=b"col1,col2\nval1,val2",
                        source_type="VFD_DRIVE_LOG",
                    )
                self.assertIn("Failed to durably register evidence metadata", str(ctx.exception))
                # Ensure storage cleanup was invoked
                self.assertTrue(mock_delete_storage.called)

    def test_production_unconfigured_repository_raises_error(self):
        """Verify production mode without DATABASE_URL rejects uploads with clear configuration error."""
        prod_repo = ProductionUnconfiguredRepository()
        rec = self._sample_record("EVD-UPL-701")
        with self.assertRaises(IngestionError) as ctx:
            prod_repo.create(rec)
        self.assertIn("Durable database persistence is not configured in production", str(ctx.exception))
        self.assertEqual(ctx.exception.status_code, 500)

    def test_health_check_safe_statuses(self):
        """Verify health check reports safe status values without credentials."""
        # When DATABASE_URL is unset in development
        with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=False):
            with patch("backend.core.config.settings.DATABASE_URL", None):
                with patch("backend.core.config.settings.ENVIRONMENT", "development"):
                    status = check_database_health()
                    self.assertEqual(status, "not_configured")

        # When DATABASE_URL is set but connection fails
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:pass@localhost:5432/db"}, clear=False):
            with patch("backend.core.config.settings.DATABASE_URL", "postgresql://test:pass@localhost:5432/db"):
                status = check_database_health()
                self.assertEqual(status, "unreachable")


if __name__ == "__main__":
    unittest.main()
