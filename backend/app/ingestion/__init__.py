"""Modular ingestion package for RETRACE multimodal evidence."""
from backend.services.upload_service import (
    ingestion_service,
    IngestionService,
    IngestionError,
    CANONICAL_SOURCE_TYPES,
    VALID_SOURCE_TYPE_CODES,
    ALLOWED_EXTENSIONS,
)
from backend.services.evidence_storage import evidence_storage, EvidenceStorageService
from backend.services.evidence_extractor import extract_evidence_metadata

__all__ = [
    "ingestion_service",
    "IngestionService",
    "IngestionError",
    "evidence_storage",
    "EvidenceStorageService",
    "extract_evidence_metadata",
    "CANONICAL_SOURCE_TYPES",
    "VALID_SOURCE_TYPE_CODES",
    "ALLOWED_EXTENSIONS",
]
