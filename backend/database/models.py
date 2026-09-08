"""Database models for RETRACE multimodal maintenance intelligence."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
    from sqlalchemy import String, Integer, Text, DateTime, JSON, Index
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    DeclarativeBase = object  # type: ignore

from backend.schemas.upload import UploadedEvidence


if HAS_SQLALCHEMY:
    class Base(DeclarativeBase):
        pass

    class UploadedEvidenceModel(Base):
        """Persistent relational storage for uploaded industrial evidence metadata.
        Raw binary evidence remains immutably in GCS; metadata is indexed here.
        """
        __tablename__ = "uploaded_evidence"

        evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
        incident_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
        source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
        original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
        stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
        content_type: Mapped[str] = mapped_column(String(128), nullable=False)
        file_size: Mapped[int] = mapped_column(Integer, nullable=False)
        asset_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
        description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
        uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
        processing_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
        sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
        
        # 'metadata' is a reserved attribute on DeclarativeBase, so mapped to column 'metadata'
        metadata_dict: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)

        __table_args__ = (
            Index("ix_uploaded_evidence_incident_id", "incident_id"),
            Index("ix_uploaded_evidence_asset_id", "asset_id"),
            Index("ix_uploaded_evidence_source_type", "source_type"),
            Index("ix_uploaded_evidence_processing_status", "processing_status"),
            Index("ix_uploaded_evidence_sha256_hash", "sha256_hash"),
            Index("ix_uploaded_evidence_uploaded_at", "uploaded_at"),
        )

        def to_pydantic(self) -> UploadedEvidence:
            """Convert SQLAlchemy model instance to domain Pydantic model."""
            uploaded_iso = (
                self.uploaded_at.isoformat()
                if hasattr(self.uploaded_at, "isoformat")
                else str(self.uploaded_at)
            )
            return UploadedEvidence(
                evidence_id=self.evidence_id,
                incident_id=self.incident_id,
                source_type=self.source_type,
                original_filename=self.original_filename,
                stored_filename=self.stored_filename,
                content_type=self.content_type,
                file_size=self.file_size,
                asset_id=self.asset_id,
                description=self.description,
                storage_uri=self.storage_uri,
                uploaded_at=uploaded_iso,
                processing_status=self.processing_status,
                sha256_hash=self.sha256_hash,
                metadata=self.metadata_dict or {},
            )

        @classmethod
        def from_pydantic(cls, item: UploadedEvidence) -> "UploadedEvidenceModel":
            """Create SQLAlchemy model instance from domain Pydantic model."""
            uploaded_at_val = item.uploaded_at
            if isinstance(uploaded_at_val, str):
                try:
                    uploaded_at_val = datetime.fromisoformat(uploaded_at_val)
                except Exception:
                    uploaded_at_val = datetime.now(timezone.utc)
            return cls(
                evidence_id=item.evidence_id,
                incident_id=item.incident_id,
                source_type=item.source_type,
                original_filename=item.original_filename,
                stored_filename=item.stored_filename,
                content_type=item.content_type,
                file_size=item.file_size,
                asset_id=item.asset_id,
                description=item.description,
                storage_uri=item.storage_uri,
                uploaded_at=uploaded_at_val,
                processing_status=item.processing_status,
                sha256_hash=item.sha256_hash,
                metadata_dict=item.metadata or {},
            )
else:
    class Base:  # type: ignore
        metadata = None

    class UploadedEvidenceModel:  # type: ignore
        pass
