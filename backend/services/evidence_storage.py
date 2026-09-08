"""Storage abstraction for industrial evidence artifacts.
Supports local development storage and Google Cloud Storage (GCS).
"""
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class EvidenceStorageService:
    def __init__(self):
        self.bucket_name = os.getenv("GCS_BUCKET_NAME", "").strip()
        # Safe local storage directory for local development or container fallback
        default_local_dir = Path(__file__).resolve().parent.parent / "data" / "evidence_storage"
        self.local_storage_dir = Path(os.getenv("LOCAL_STORAGE_DIR", str(default_local_dir)))
        self._gcs_client = None

        if self.bucket_name:
            try:
                from google.cloud import storage
                # On Cloud Run, Application Default Credentials (ADC) are resolved automatically
                self._gcs_client = storage.Client()
                logger.info(f"EvidenceStorageService initialized with GCS bucket: {self.bucket_name}")
            except Exception as e:
                logger.warning(
                    f"GCS_BUCKET_NAME was specified ({self.bucket_name}), but failed to initialize GCS client: {e}. "
                    "Falling back to local storage."
                )
                self._gcs_client = None

    @property
    def is_gcs_active(self) -> bool:
        return bool(self.bucket_name and self._gcs_client)

    def _get_object_path(self, incident_id: str, evidence_id: str, filename: str) -> str:
        return f"incidents/{incident_id}/evidence/{evidence_id}/{filename}"

    def save_file(
        self,
        incident_id: str,
        evidence_id: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Saves raw evidence file immutably. Returns a safe, credential-free storage URI."""
        object_path = self._get_object_path(incident_id, evidence_id, filename)

        if self.is_gcs_active:
            try:
                bucket = self._gcs_client.bucket(self.bucket_name)
                blob = bucket.blob(object_path)
                if blob.exists():
                    raise ValueError(f"Evidence object already exists at {object_path}. Evidence is immutable.")
                blob.upload_from_string(content, content_type=content_type)
                return f"gs://{self.bucket_name}/{object_path}"
            except Exception as e:
                logger.error(f"Failed to upload evidence to GCS: {e}. Falling back to local storage.")

        # Local development fallback
        target_path = self.local_storage_dir / object_path
        if target_path.exists():
            raise ValueError(f"Evidence file already exists at {object_path}. Evidence is immutable.")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(content)

        return f"file://local/{object_path}"

    def get_file(self, incident_id: str, evidence_id: str, filename: str) -> Optional[bytes]:
        """Retrieves raw evidence file content."""
        object_path = self._get_object_path(incident_id, evidence_id, filename)

        if self.is_gcs_active:
            try:
                bucket = self._gcs_client.bucket(self.bucket_name)
                blob = bucket.blob(object_path)
                if blob.exists():
                    return blob.download_as_bytes()
            except Exception as e:
                logger.error(f"Failed to download evidence from GCS: {e}")

        # Local development fallback
        target_path = self.local_storage_dir / object_path
        if target_path.exists() and target_path.is_file():
            with open(target_path, "rb") as f:
                return f.read()

        return None

    def delete_file(self, incident_id: str, evidence_id: str, filename: str) -> bool:
        """Deletes raw evidence file object."""
        object_path = self._get_object_path(incident_id, evidence_id, filename)
        deleted = False

        if self.is_gcs_active:
            try:
                bucket = self._gcs_client.bucket(self.bucket_name)
                blob = bucket.blob(object_path)
                if blob.exists():
                    blob.delete()
                    deleted = True
            except Exception as e:
                logger.error(f"Failed to delete evidence from GCS: {e}")

        target_path = self.local_storage_dir / object_path
        if target_path.exists() and target_path.is_file():
            try:
                target_path.unlink()
                deleted = True
                # Clean up empty parent directory if empty
                if target_path.parent.exists() and not any(target_path.parent.iterdir()):
                    target_path.parent.rmdir()
            except Exception as e:
                logger.error(f"Failed to delete local evidence file: {e}")

        return deleted

evidence_storage = EvidenceStorageService()
