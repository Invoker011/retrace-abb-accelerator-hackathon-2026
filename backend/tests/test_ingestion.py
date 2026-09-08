"""Tests for industrial evidence upload, validation, and storage workflows."""
import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_valid_csv_upload():
    """Verify valid CSV file is uploaded, metadata parsed, and registered."""
    csv_content = b"Timestamp,Current_A,Voltage_V,Speed_RPM\n10:14:01,245.2,398.5,1480\n10:14:02,260.1,397.8,1475"
    files = {"file": ("drive_sample.csv", csv_content, "text/csv")}
    data = {
        "source_type": "VFD_DRIVE_LOG",
        "asset_id": "VFD-204",
        "description": "VFD high-frequency log sample during current spike",
    }
    response = client.post("/api/incidents/INC-2026-001/evidence/upload", files=files, data=data)
    assert response.status_code == 201
    upload = response.json()
    assert upload["incidentId"] == "INC-2026-001"
    assert upload["sourceType"] == "VFD_DRIVE_LOG"
    assert upload["assetId"] == "VFD-204"
    assert upload["processingStatus"] == "UPLOADED"
    assert "sha256Hash" in upload
    assert len(upload["sha256Hash"]) == 64
    assert upload["metadata"]["format"] == "csv"
    assert upload["metadata"]["row_count"] == 2
    assert "columns" in upload["metadata"]
    assert "Current_A" in upload["metadata"]["columns"]

    # Verify retrieval via uploads list
    list_res = client.get("/api/incidents/INC-2026-001/evidence/uploads")
    assert list_res.status_code == 200
    uploads_list = list_res.json()
    assert any(u["evidenceId"] == upload["evidenceId"] for u in uploads_list)

    # Verify retrieval by individual evidence ID
    single_res = client.get(f"/api/evidence/uploads/{upload['evidenceId']}")
    assert single_res.status_code == 200
    assert single_res.json()["evidenceId"] == upload["evidenceId"]

def test_valid_pdf_upload():
    """Verify valid PDF document upload with %PDF- header."""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    files = {"file": ("pump_datasheet.pdf", pdf_content, "application/pdf")}
    data = {
        "source_type": "ENGINEERING_DOCUMENT",
        "asset_id": "P-204",
        "description": "OEM Pump specifications and vibration envelope",
    }
    response = client.post("/api/incidents/INC-2026-001/evidence/upload", files=files, data=data)
    assert response.status_code == 201
    upload = response.json()
    assert upload["sourceType"] == "ENGINEERING_DOCUMENT"
    assert upload["metadata"]["format"] == "pdf"
    assert upload["metadata"]["valid_header"] is True

def test_valid_image_upload():
    """Verify valid PNG image upload with dimensions extraction."""
    # 1x1 valid PNG bytes
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    files = {"file": ("bearing_photo.png", png_bytes, "image/png")}
    data = {
        "source_type": "TECHNICIAN_FIELD_EVIDENCE",
        "asset_id": "M-204",
        "description": "Technician photograph of non-drive end bearing housing",
    }
    response = client.post("/api/incidents/INC-2026-001/evidence/upload", files=files, data=data)
    assert response.status_code == 201
    upload = response.json()
    assert upload["sourceType"] == "TECHNICIAN_FIELD_EVIDENCE"
    assert upload["metadata"]["format"] == "image"
    assert upload["metadata"]["width"] == 1
    assert upload["metadata"]["height"] == 1

def test_unsupported_executable_rejection():
    """Verify executable file is rejected with HTTP 400."""
    exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00"
    files = {"file": ("malicious_tool.exe", exe_content, "application/x-msdownload")}
    data = {"source_type": "PLC_SCADA"}
    response = client.post("/api/incidents/INC-2026-001/evidence/upload", files=files, data=data)
    assert response.status_code == 400
    assert "unsupported file extension" in response.json()["detail"].lower()

def test_double_extension_executable_trick_rejection():
    """Verify nested executable extension segments like .exe.png are rejected."""
    fake_png = b"\x89PNG\r\n\x1a\nfake"
    files = {"file": ("report.exe.png", fake_png, "image/png")}
    data = {"source_type": "TECHNICIAN_FIELD_EVIDENCE"}
    response = client.post("/api/incidents/INC-2026-001/evidence/upload", files=files, data=data)
    assert response.status_code == 400
    assert "dangerous file pattern" in response.json()["detail"].lower()

def test_oversized_file_rejection():
    """Verify files larger than 20MB are rejected with HTTP 400."""
    oversized_content = b"X" * (20 * 1024 * 1024 + 1024)  # 20MB + 1KB
    files = {"file": ("massive_telemetry.csv", oversized_content, "text/csv")}
    data = {"source_type": "HISTORIAN"}
    response = client.post("/api/incidents/INC-2026-001/evidence/upload", files=files, data=data)
    assert response.status_code == 400
    assert "exceeds" in response.json()["detail"].lower()

def test_unknown_incident_rejection():
    """Verify uploads to non-existent incidents return 404."""
    csv_content = b"header1,header2\nval1,val2"
    files = {"file": ("notes.txt", csv_content, "text/plain")}
    data = {"source_type": "TECHNICIAN_FIELD_EVIDENCE"}
    response = client.post("/api/incidents/INC-NONEXISTENT-999/evidence/upload", files=files, data=data)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_safe_filename_handling():
    """Verify path traversal sequences and unsafe characters are stripped from filename."""
    csv_content = b"colA,colB\n1,2"
    files = {"file": ("../../../../etc/passwd_dump.csv", csv_content, "text/csv")}
    data = {"source_type": "HISTORIAN"}
    response = client.post("/api/incidents/INC-2026-001/evidence/upload", files=files, data=data)
    assert response.status_code == 201
    upload = response.json()
    assert ".." not in upload["originalFilename"]
    assert "/" not in upload["originalFilename"]
    assert "\\" not in upload["originalFilename"]

def test_evidence_deletion():
    """Verify uploaded evidence artifact can be deleted cleanly."""
    txt_content = b"Shift handover report: audible noise near suction strainer."
    files = {"file": ("rover_note.txt", txt_content, "text/plain")}
    data = {"source_type": "TECHNICIAN_FIELD_EVIDENCE"}
    create_res = client.post("/api/incidents/INC-2026-001/evidence/upload", files=files, data=data)
    assert create_res.status_code == 201
    evidence_id = create_res.json()["evidenceId"]

    # Delete the evidence
    del_res = client.delete(f"/api/evidence/uploads/{evidence_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Subsequent retrieval returns 404
    get_res = client.get(f"/api/evidence/uploads/{evidence_id}")
    assert get_res.status_code == 404
