"""Repository layer for uploaded industrial evidence metadata."""
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from backend.core.config import settings
from backend.database.models import UploadedEvidenceModel
from backend.database.session import get_db_session, get_engine
from backend.schemas.upload import UploadedEvidence

logger = logging.getLogger("retrace.repository")


class UploadedEvidenceRepositoryInterface(ABC):
    """Abstract interface for uploaded evidence repository."""

    @abstractmethod
    def create(self, record: UploadedEvidence) -> UploadedEvidence:
        """Persist newly uploaded evidence metadata."""
        pass

    @abstractmethod
    def get_by_id(self, evidence_id: str) -> Optional[UploadedEvidence]:
        """Retrieve uploaded evidence metadata by evidence_id."""
        pass

    @abstractmethod
    def get_by_incident(self, incident_id: str) -> List[UploadedEvidence]:
        """Retrieve all uploaded evidence items associated with an incident."""
        pass

    @abstractmethod
    def delete(self, evidence_id: str) -> bool:
        """Delete uploaded evidence metadata by evidence_id."""
        pass

    @abstractmethod
    def find_by_hash(self, sha256_hash: str) -> List[UploadedEvidence]:
        """Find uploaded evidence metadata matching an exact SHA-256 hash."""
        pass


class PostgresUploadedEvidenceRepository(UploadedEvidenceRepositoryInterface):
    """PostgreSQL implementation using SQLAlchemy 2.x session and parameterized queries."""

    def create(self, record: UploadedEvidence) -> UploadedEvidence:
        try:
            from sqlalchemy.orm import Session
        except ImportError:
            raise RuntimeError("SQLAlchemy must be installed to use PostgresUploadedEvidenceRepository")

        model_instance = UploadedEvidenceModel.from_pydantic(record)
        with get_db_session() as session:
            if session is None:
                raise RuntimeError("Failed to acquire database session for evidence persistence")
            session.add(model_instance)
            session.flush()
            return model_instance.to_pydantic()

    def get_by_id(self, evidence_id: str) -> Optional[UploadedEvidence]:
        try:
            from sqlalchemy import select
        except ImportError:
            return None

        with get_db_session() as session:
            if session is None:
                return None
            stmt = select(UploadedEvidenceModel).where(
                UploadedEvidenceModel.evidence_id == evidence_id.strip()
            )
            result = session.execute(stmt).scalar_one_or_none()
            if result:
                return result.to_pydantic()
            return None

    def get_by_incident(self, incident_id: str) -> List[UploadedEvidence]:
        try:
            from sqlalchemy import select
        except ImportError:
            return []

        with get_db_session() as session:
            if session is None:
                return []
            stmt = (
                select(UploadedEvidenceModel)
                .where(UploadedEvidenceModel.incident_id == incident_id.strip())
                .order_by(UploadedEvidenceModel.uploaded_at.desc())
            )
            results = session.execute(stmt).scalars().all()
            return [r.to_pydantic() for r in results]

    def delete(self, evidence_id: str) -> bool:
        try:
            from sqlalchemy import select
        except ImportError:
            return False

        with get_db_session() as session:
            if session is None:
                return False
            stmt = select(UploadedEvidenceModel).where(
                UploadedEvidenceModel.evidence_id == evidence_id.strip()
            )
            result = session.execute(stmt).scalar_one_or_none()
            if not result:
                return False
            session.delete(result)
            return True

    def find_by_hash(self, sha256_hash: str) -> List[UploadedEvidence]:
        try:
            from sqlalchemy import select
        except ImportError:
            return []

        with get_db_session() as session:
            if session is None:
                return []
            stmt = select(UploadedEvidenceModel).where(
                UploadedEvidenceModel.sha256_hash == sha256_hash.strip().lower()
            )
            results = session.execute(stmt).scalars().all()
            return [r.to_pydantic() for r in results]


class InMemoryUploadedEvidenceRepository(UploadedEvidenceRepositoryInterface):
    """In-memory repository fallback strictly for local/development environments."""

    def __init__(self):
        self._records: Dict[str, UploadedEvidence] = {}

    def create(self, record: UploadedEvidence) -> UploadedEvidence:
        self._records[record.evidence_id] = record
        return record

    def get_by_id(self, evidence_id: str) -> Optional[UploadedEvidence]:
        for eid, rec in self._records.items():
            if eid.upper() == evidence_id.upper():
                return rec
        return None

    def get_by_incident(self, incident_id: str) -> List[UploadedEvidence]:
        return [
            rec for rec in self._records.values()
            if rec.incident_id.upper() == incident_id.upper()
        ]

    def delete(self, evidence_id: str) -> bool:
        for eid in list(self._records.keys()):
            if eid.upper() == evidence_id.upper():
                del self._records[eid]
                return True
        return False

    def find_by_hash(self, sha256_hash: str) -> List[UploadedEvidence]:
        h = sha256_hash.strip().lower()
        return [
            rec for rec in self._records.values()
            if rec.sha256_hash.lower() == h
        ]


class ProductionUnconfiguredRepository(UploadedEvidenceRepositoryInterface):
    """Safety guard: in production mode without DATABASE_URL, prevents silent data loss."""

    def create(self, record: UploadedEvidence) -> UploadedEvidence:
        from backend.services.upload_service import IngestionError
        raise IngestionError(
            "Durable database persistence is not configured in production. Evidence upload requires a configured DATABASE_URL.",
            status_code=500,
        )

    def get_by_id(self, evidence_id: str) -> Optional[UploadedEvidence]:
        return None

    def get_by_incident(self, incident_id: str) -> List[UploadedEvidence]:
        return []

    def delete(self, evidence_id: str) -> bool:
        return False

    def find_by_hash(self, sha256_hash: str) -> List[UploadedEvidence]:
        return []


_repository_instance: Optional[UploadedEvidenceRepositoryInterface] = None


def get_uploaded_evidence_repository() -> UploadedEvidenceRepositoryInterface:
    """Factory that returns the appropriate repository according to environment and DATABASE_URL."""
    global _repository_instance
    if _repository_instance is not None:
        return _repository_instance

    engine = get_engine()
    if engine is not None:
        _repository_instance = PostgresUploadedEvidenceRepository()
        return _repository_instance

    # DATABASE_URL is not configured
    if settings.ENVIRONMENT == "production":
        logger.error(
            "[RETRACE] DATABASE_URL is not configured in production. Evidence upload persistence disabled."
        )
        _repository_instance = ProductionUnconfiguredRepository()
        return _repository_instance

    # Local development mode
    print("[RETRACE] PostgreSQL not configured - using development in-memory metadata repository")
    logger.info(
        "[RETRACE] PostgreSQL not configured - using development in-memory metadata repository"
    )
    _repository_instance = InMemoryUploadedEvidenceRepository()
    return _repository_instance


def set_uploaded_evidence_repository(repo: Optional[UploadedEvidenceRepositoryInterface]) -> None:
    """Allows test fixtures or custom setups to inject a repository instance."""
    global _repository_instance
    _repository_instance = repo
