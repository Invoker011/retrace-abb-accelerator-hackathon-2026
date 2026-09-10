"""Tests for industrial evidence upload, validation, and storage workflows."""
import io
import unittest

try:
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    HAS_TESTCLIENT = True
except Exception:
    client = None  # type: ignore
    HAS_TESTCLIENT = False

from backend.services.upload_service import (
    IngestionService,
    IngestionError,
    ingestion_service,
)
from backend.repositories.uploaded_evidence_repository import InMemoryUploadedEvidenceRepository


class TestEvidenceIngestion(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryUploadedEvidenceRepository()
        self.service = IngestionService(repo=self.repo)

    def test_direct_valid_csv_ingest(self):
        """Verify valid CSV file is uploaded, metadata parsed, and registered."""
        csv_content = b"Timestamp,Current_A,Voltage_V,Speed_RPM\n10:14:01,245.2,398.5,1480\n10:14:02,260.1,397.8,1475"
        record = self.service.upload_evidence(
            incident_id="INC-2026-001",
            source_type="VFD_DRIVE_LOG",
            original_filename="drive_sample.csv",
            file_bytes=csv_content,
            content_type="text/csv",
            asset_id="VFD-204",
            description="VFD high-frequency log sample during current spike",
        )
        self.assertEqual(record.incident_id, "INC-2026-001")
        self.assertEqual(record.source_type, "VFD_DRIVE_LOG")
        self.assertEqual(record.asset_id, "VFD-204")
        self.assertEqual(record.processing_status, "UPLOADED")
        self.assertEqual(len(record.sha256_hash), 64)
        self.assertEqual(record.metadata.get("format"), "csv")
        self.assertEqual(record.metadata.get("row_count"), 2)
        self.assertIn("Current_A", record.metadata.get("columns", []))

    def test_direct_valid_pdf_ingest(self):
        """Verify valid PDF document upload with %PDF- header."""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        record = self.service.upload_evidence(
            incident_id="INC-2026-001",
            source_type="ENGINEERING_DOCUMENT",
            original_filename="pump_datasheet.pdf",
            file_bytes=pdf_content,
            content_type="application/pdf",
            asset_id="P-204",
            description="OEM Pump specifications and vibration envelope",
        )
        self.assertEqual(record.source_type, "ENGINEERING_DOCUMENT")
        self.assertEqual(record.metadata.get("format"), "pdf")
        self.assertTrue(record.metadata.get("valid_header"))

    def test_direct_valid_image_ingest(self):
        """Verify valid PNG image upload with dimensions extraction."""
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        record = self.service.upload_evidence(
            incident_id="INC-2026-001",
            source_type="TECHNICIAN_FIELD_EVIDENCE",
            original_filename="bearing_photo.png",
            file_bytes=png_bytes,
            content_type="image/png",
            asset_id="M-204",
            description="Technician photograph of non-drive end bearing housing",
        )
        self.assertEqual(record.source_type, "TECHNICIAN_FIELD_EVIDENCE")
        self.assertEqual(record.metadata.get("format"), "image")
        self.assertEqual(record.metadata.get("width"), 1)
        self.assertEqual(record.metadata.get("height"), 1)

    def test_direct_unsupported_executable_rejection(self):
        """Verify executable file is rejected with IngestionError."""
        exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00"
        with self.assertRaises(IngestionError) as ctx:
            self.service.upload_evidence(
                incident_id="INC-2026-001",
                source_type="PLC_SCADA",
                original_filename="malicious_tool.exe",
                file_bytes=exe_content,
                content_type="application/x-msdownload",
            )
        self.assertIn("unsupported file extension", str(ctx.exception).lower())

    def test_direct_double_extension_executable_trick_rejection(self):
        """Verify nested executable extension segments like .exe.png are rejected."""
        fake_png = b"\x89PNG\r\n\x1a\nfake"
        with self.assertRaises(IngestionError) as ctx:
            self.service.upload_evidence(
                incident_id="INC-2026-001",
                source_type="TECHNICIAN_FIELD_EVIDENCE",
                original_filename="report.exe.png",
                file_bytes=fake_png,
                content_type="image/png",
            )
        self.assertIn("dangerous file pattern", str(ctx.exception).lower())

    def test_direct_oversized_file_rejection(self):
        """Verify files larger than 20MB are rejected."""
        oversized_content = b"X" * (20 * 1024 * 1024 + 1024)
        with self.assertRaises(IngestionError) as ctx:
            self.service.upload_evidence(
                incident_id="INC-2026-001",
                source_type="HISTORIAN",
                original_filename="massive_telemetry.csv",
                file_bytes=oversized_content,
                content_type="text/csv",
            )
        self.assertIn("exceeds", str(ctx.exception).lower())

    def test_direct_safe_filename_handling(self):
        """Verify path traversal sequences and unsafe characters are stripped."""
        sanitized = self.service.sanitize_filename("../../../../etc/passwd_dump.csv")
        self.assertNotIn("..", sanitized)
        self.assertNotIn("/", sanitized)
        self.assertNotIn("\\", sanitized)

    def test_direct_evidence_deletion(self):
        """Verify uploaded evidence artifact can be deleted cleanly."""
        txt_content = b"Shift handover report: audible noise near suction strainer."
        record = self.service.upload_evidence(
            incident_id="INC-2026-001",
            source_type="TECHNICIAN_FIELD_EVIDENCE",
            original_filename="rover_note.txt",
            file_bytes=txt_content,
            content_type="text/plain",
        )
        self.assertIsNotNone(self.service.get_upload_by_id(record.evidence_id))
        deleted = self.service.delete_upload(record.evidence_id)
        self.assertTrue(deleted)
        self.assertIsNone(self.service.get_upload_by_id(record.evidence_id))

    @unittest.skipUnless(HAS_TESTCLIENT, "TestClient requires httpx")
    def test_api_valid_csv_upload(self):
        csv_content = b"Timestamp,Current_A,Voltage_V,Speed_RPM\n10:14:01,245.2,398.5,1480\n10:14:02,260.1,397.8,1475"
        files = {"file": ("drive_sample.csv", csv_content, "text/csv")}
        data = {
            "source_type": "VFD_DRIVE_LOG",
            "asset_id": "VFD-204",
            "description": "VFD high-frequency log sample during current spike",
        }
        response = client.post("/api/incidents/INC-2026-001/evidence/upload", files=files, data=data)
        self.assertEqual(response.status_code, 201)
        upload = response.json()
        self.assertEqual(upload["incidentId"], "INC-2026-001")
        self.assertEqual(upload["sourceType"], "VFD_DRIVE_LOG")


if __name__ == "__main__":
    unittest.main()

