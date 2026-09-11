"""Upload and ingestion orchestration service for industrial evidence."""
import os
import re
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.schemas.upload import UploadedEvidence
from backend.services.evidence_storage import evidence_storage
from backend.services.evidence_extractor import extract_evidence_metadata
from backend.services.incident_service import incident_service
from backend.repositories.uploaded_evidence_repository import (
    UploadedEvidenceRepositoryInterface,
    get_uploaded_evidence_repository,
)

logger = logging.getLogger("retrace.ingestion")

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

# Supported evidence categories and canonical mappings
CANONICAL_SOURCE_TYPES: Dict[str, str] = {
    "PLC_SCADA": "PLC / SCADA",
    "PLC / SCADA": "PLC_SCADA",
    "VFD_DRIVE_LOG": "VFD / Drive Logs",
    "VFD / Drive Logs": "VFD_DRIVE_LOG",
    "HISTORIAN": "Historian Data",
    "Historian Data": "HISTORIAN",
    "ENGINEERING_DOCUMENT": "Engineering Documents",
    "Engineering Documents": "ENGINEERING_DOCUMENT",
    "MAINTENANCE_INSPECTION": "Maintenance / Inspection Records",
    "Maintenance / Inspection Records": "MAINTENANCE_INSPECTION",
    "TECHNICIAN_FIELD_EVIDENCE": "Technician Notes & Photos",
    "Technician Notes & Photos": "TECHNICIAN_FIELD_EVIDENCE",
}

VALID_SOURCE_TYPE_CODES = {
    "PLC_SCADA",
    "VFD_DRIVE_LOG",
    "HISTORIAN",
    "ENGINEERING_DOCUMENT",
    "MAINTENANCE_INSPECTION",
    "TECHNICIAN_FIELD_EVIDENCE",
}

ALLOWED_EXTENSIONS = {".csv", ".pdf", ".txt", ".jpg", ".jpeg", ".png"}

BANNED_SUBSTRINGS = {
    "exe", "bat", "cmd", "sh", "bin", "py", "js", "vbs", "msi", "scr", "ps1",
    "php", "asp", "aspx", "cgi", "pl", "jar", "war", "dll", "so", "elf", "app"
}

ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/csv",
    "text/plain",
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "application/octet-stream",  # Often sent by browsers for generic CSV or binary
}

class IngestionError(Exception):
    """Domain exception for ingestion/validation failures."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class IngestionService:
    def __init__(self, repo: Optional[UploadedEvidenceRepositoryInterface] = None):
        self._custom_repo = repo

    @property
    def repo(self) -> UploadedEvidenceRepositoryInterface:
        if self._custom_repo is not None:
            return self._custom_repo
        return get_uploaded_evidence_repository()

    @property
    def _uploads(self) -> Dict[str, UploadedEvidence]:
        """Backward compatibility helper for tests inspecting internal dictionary."""
        current_repo = self.repo
        if hasattr(current_repo, "_records"):
            return getattr(current_repo, "_records")
        return {}

    def normalize_source_type(self, raw_source_type: str) -> str:
        """Validates and normalizes source type to canonical code."""
        if not raw_source_type:
            raise IngestionError(
                "Source type is required. Must be one of: " + ", ".join(sorted(VALID_SOURCE_TYPE_CODES))
            )
        cleaned = raw_source_type.strip()
        if cleaned in VALID_SOURCE_TYPE_CODES:
            return cleaned
        if cleaned in CANONICAL_SOURCE_TYPES:
            return CANONICAL_SOURCE_TYPES[cleaned]
        # Check case-insensitive match
        upper_cleaned = cleaned.upper().replace(" ", "_").replace("/", "_")
        for valid in VALID_SOURCE_TYPE_CODES:
            if upper_cleaned == valid or valid in upper_cleaned:
                return valid
        raise IngestionError(
            f"Invalid source_type '{raw_source_type}'. Must be one of: {', '.join(sorted(VALID_SOURCE_TYPE_CODES))}"
        )

    def sanitize_filename(self, original_filename: str) -> str:
        """Sanitizes filename against path traversal, control chars, and unsafe names."""
        if not original_filename:
            raise IngestionError("Uploaded file must have a valid filename.")
        
        # Strip path traversal components
        base_name = os.path.basename(original_filename.replace("\\", "/"))
        # Remove any path traversal sequences
        base_name = re.sub(r"\.\.+", ".", base_name)
        # Keep only alphanumeric, dash, underscore, dot, and space
        sanitized = re.sub(r"[^a-zA-Z0-9._\- ]", "_", base_name).strip()
        if not sanitized or sanitized == ".":
            sanitized = f"evidence_{uuid.uuid4().hex[:6]}"
        return sanitized

    def validate_file(self, filename: str, content_type: Optional[str], file_bytes: bytes) -> str:
        """Validates file extension, double extensions, content type, and file size."""
        # 1. Size check
        if len(file_bytes) == 0:
            raise IngestionError("Uploaded file is empty (0 bytes).")
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise IngestionError(
                f"File size ({len(file_bytes)} bytes) exceeds the maximum allowed upload limit of 20MB."
            )

        # 2. Extension check
        parts = filename.lower().split(".")
        if len(parts) < 2:
            raise IngestionError("Uploaded file must have a valid extension (.csv, .pdf, .txt, .jpg, .jpeg, .png).")
        
        ext = "." + parts[-1]
        if ext not in ALLOWED_EXTENSIONS:
            raise IngestionError(
                f"Unsupported file extension '{ext}'. Accepted formats are: .csv, .pdf, .txt, .jpg, .jpeg, .png"
            )

        # 3. Double-extension / executable trick prevention
        for segment in parts[:-1]:
            if segment in BANNED_SUBSTRINGS:
                raise IngestionError(
                    f"Dangerous file pattern detected: nested executable extension segment '{segment}' is prohibited."
                )

        # 4. MIME type check if supplied
        if content_type:
            cleaned_ct = content_type.split(";")[0].strip().lower()
            if cleaned_ct and cleaned_ct not in ALLOWED_MIME_TYPES:
                # Disallow explicit executable or script MIME types
                if any(x in cleaned_ct for x in ("executable", "javascript", "script", "php", "sh", "batch")):
                    raise IngestionError(f"Forbidden MIME type detected: {cleaned_ct}")

        # 5. Magic byte verification
        if ext in (".jpg", ".jpeg"):
            if not file_bytes.startswith(b"\xff\xd8\xff"):
                raise IngestionError("File extension is .jpg/.jpeg but content does not have a valid JPEG header.")
        elif ext == ".png":
            if not file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                raise IngestionError("File extension is .png but content does not have a valid PNG header.")
        elif ext == ".pdf":
            if not file_bytes.startswith(b"%PDF-"):
                raise IngestionError("File extension is .pdf but content does not have a valid PDF header (%PDF-).")

        return ext

    def upload_evidence(
        self,
        incident_id: str,
        original_filename: str,
        content_type: Optional[str],
        file_bytes: bytes,
        source_type: str,
        asset_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> UploadedEvidence:
        """Main ingestion entry point: validates, stores raw object, extracts metadata, registers provenance."""
        # 1. Validate incident exists
        incident = incident_service.get_incident_by_id(incident_id)
        if not incident:
            raise IngestionError(f"Incident '{incident_id}' not found.", status_code=404)

        # 2. Validate and normalize source category
        canonical_source_type = self.normalize_source_type(source_type)

        # 3. Sanitize filename
        safe_filename = self.sanitize_filename(original_filename)

        # 4. Validate file content and attributes
        self.validate_file(safe_filename, content_type, file_bytes)

        # 5. Compute SHA-256 checksum for audit immutability
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        # 6. Generate server-side unique evidence ID
        evidence_id = f"EVD-UPL-{uuid.uuid4().hex[:8].upper()}"
        stored_filename = f"{evidence_id}_{safe_filename}"

        # 7. Persist raw file to storage layer (GCS or Local Development)
        storage_uri = evidence_storage.save_file(
            incident_id=incident_id,
            evidence_id=evidence_id,
            filename=stored_filename,
            content=file_bytes,
            content_type=content_type or "application/octet-stream",
        )

        # 8. Deterministic non-AI metadata extraction
        extracted_meta = extract_evidence_metadata(file_bytes, safe_filename)

        # Determine retrieval eligibility for uploaded evidence
        from backend.services.evidence_eligibility import is_evidence_retrieval_eligible
        desc_str = description.strip() if description else None
        is_eligible = is_evidence_retrieval_eligible({
            "original_filename": safe_filename,
            "description": desc_str,
            "metadata": extracted_meta,
        })
        if not is_eligible:
            extracted_meta["retrieval_eligible"] = False
            if not extracted_meta.get("use_type"):
                extracted_meta["use_type"] = "test"

        # 9. Register provenance record
        now_iso = datetime.now(timezone.utc).isoformat()
        uploaded_record = UploadedEvidence(
            evidence_id=evidence_id,
            incident_id=incident_id,
            source_type=canonical_source_type,
            original_filename=safe_filename,
            stored_filename=stored_filename,
            content_type=content_type or "application/octet-stream",
            file_size=len(file_bytes),
            asset_id=asset_id.strip() if asset_id else None,
            description=desc_str,
            storage_uri=storage_uri,
            uploaded_at=now_iso,
            processing_status="UPLOADED",
            sha256_hash=sha256_hash,
            retrieval_eligible=is_eligible,
            metadata=extracted_meta,
        )

        # 10. Persist metadata to database via repository
        try:
            saved_record = self.repo.create(uploaded_record)
            return saved_record
        except Exception as db_err:
            # Consistency recovery: Attempt to delete the newly created raw storage object
            # so RETRACE does not intentionally leave orphaned evidence files
            try:
                evidence_storage.delete_file(
                    incident_id=incident_id,
                    evidence_id=evidence_id,
                    filename=stored_filename,
                )
            except Exception as cleanup_err:
                logger.warning(
                    "[RETRACE] Failed to cleanup raw evidence file during database failure: %s",
                    type(cleanup_err).__name__,
                )
            # Log failure safely without exposing credentials or internal connection strings
            logger.error(
                "[RETRACE] Failed to persist uploaded evidence metadata to database: %s",
                type(db_err).__name__,
            )
            if isinstance(db_err, IngestionError):
                raise db_err
            raise IngestionError(
                "Failed to durably register evidence metadata in database.",
                status_code=500,
            )

    def get_uploads_for_incident(self, incident_id: str) -> List[UploadedEvidence]:
        """Returns all uploaded evidence items for a given incident from repository."""
        return self.repo.get_by_incident(incident_id)

    def get_upload_by_id(self, evidence_id: str) -> Optional[UploadedEvidence]:
        """Retrieves a single uploaded evidence item by ID from repository."""
        return self.repo.get_by_id(evidence_id)

    def delete_upload(self, evidence_id: str) -> bool:
        """Deletes an uploaded evidence record and its underlying raw storage object.
        1. Retrieve metadata from repository.
        2. Determine the storage object from server-side stored metadata.
        3. Delete the raw object through EvidenceStorageService.
        4. Delete the metadata record from repository.
        """
        record = self.get_upload_by_id(evidence_id)
        if not record:
            return False

        # Remove raw file from storage (safe handling if already missing)
        try:
            evidence_storage.delete_file(
                incident_id=record.incident_id,
                evidence_id=record.evidence_id,
                filename=record.stored_filename,
            )
        except Exception as storage_err:
            logger.warning(
                "[RETRACE] Storage delete warning for %s: %s",
                record.stored_filename,
                type(storage_err).__name__,
            )

        # Delete metadata record from repository
        deleted = self.repo.delete(record.evidence_id)
        return deleted

ingestion_service = IngestionService()
