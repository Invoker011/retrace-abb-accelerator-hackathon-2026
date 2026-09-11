"""Vector Index and Semantic Search orchestration service for RETRACE.

Coordinates factual chunking, Vertex AI embedding generation, Qdrant synchronization,
idempotent reconciliation, and incident-scoped semantic retrieval.
"""
import logging
from typing import Any, Dict, List, Optional

from backend.core.config import settings
from backend.services.incident_service import incident_service
from backend.repositories.uploaded_evidence_repository import (
    UploadedEvidenceRepositoryInterface,
    get_uploaded_evidence_repository,
)
from backend.vector.models import (
    EvidenceChunk,
    SemanticSearchResultItem,
    SemanticSearchResponse,
    VectorSyncResponse,
)
from backend.vector.embedding import (
    EmbeddingProvider,
    GeminiEmbeddingProvider,
    FakeEmbeddingProvider,
    EmbeddingProviderError,
)
from backend.vector.chunking import EvidenceChunkingService
from backend.vector.repository import (
    EvidenceVectorRepository,
    QdrantEvidenceVectorRepository,
    InMemoryEvidenceVectorRepository,
)
from backend.services.evidence_eligibility import is_evidence_retrieval_eligible

logger = logging.getLogger("retrace.vector")


class VectorServiceError(Exception):
    """Domain exception for vector indexing and semantic retrieval failures."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class VectorIndexService:
    """Service managing evidence vector synchronization and similarity search."""

    def __init__(
        self,
        vector_repo: Optional[EvidenceVectorRepository] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        chunking_service: Optional[EvidenceChunkingService] = None,
        upload_repo: Optional[UploadedEvidenceRepositoryInterface] = None,
    ):
        self._vector_repo = vector_repo
        self._embedding_provider = embedding_provider
        self._chunking_service = chunking_service or EvidenceChunkingService()
        self._upload_repo = upload_repo

    @property
    def vector_repo(self) -> EvidenceVectorRepository:
        if self._vector_repo is not None:
            return self._vector_repo
        
        # Production default: require Qdrant configuration
        if not settings.QDRANT_URL:
            raise VectorServiceError(
                "Qdrant vector database is not configured. Set QDRANT_URL to enable semantic retrieval.",
                status_code=503,
            )
        return QdrantEvidenceVectorRepository()

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        if self._embedding_provider is not None:
            return self._embedding_provider

        return GeminiEmbeddingProvider()

    @property
    def upload_repo(self) -> UploadedEvidenceRepositoryInterface:
        if self._upload_repo is not None:
            return self._upload_repo
        return get_uploaded_evidence_repository()

    @property
    def chunking_service(self) -> EvidenceChunkingService:
        return self._chunking_service

    def sync_incident(self, incident_id: str) -> Dict[str, Any]:
        """Synchronize all factual evidence for an incident into Qdrant.

        Flow:
        1. Validate incident exists
        2. Fetch synthetic evidence through RETRACE service layer
        3. Fetch persistent uploaded evidence through PostgreSQL repository
        4. Build factual EvidenceChunks without fabricating observations
        5. Generate 768-dim embeddings via embedding provider
        6. Ensure collection exists with 768-dim COSINE configuration
        7. Reconcile / delete existing RETRACE points for THIS incident
        8. Upsert deterministic points
        """
        if not incident_id or not incident_id.strip():
            raise VectorServiceError("A valid incident_id is required.", status_code=400)

        incident = incident_service.get_incident_by_id(incident_id)
        if not incident:
            raise VectorServiceError(f"Incident '{incident_id}' not found.", status_code=404)

        try:
            from backend.services.evidence_eligibility import is_evidence_retrieval_eligible
            # 1. Fetch synthetic evidence (filter retrieval-eligible)
            raw_synthetic = incident_service.get_incident_evidence(incident_id)
            synthetic_evidence = [s for s in raw_synthetic if is_evidence_retrieval_eligible(s)]

            # 2. Fetch persistent uploaded evidence (filter retrieval-eligible)
            raw_uploaded = self.upload_repo.get_by_incident(incident_id)
            uploaded_evidence = [u for u in raw_uploaded if is_evidence_retrieval_eligible(u)]

            # 3. Build factual chunks
            chunks = self.chunking_service.build_chunks_for_incident(
                incident_id=incident_id,
                synthetic_evidence=synthetic_evidence,
                uploaded_evidence=uploaded_evidence,
            )

            total_evidence_processed = len(synthetic_evidence) + len(uploaded_evidence)

            if not chunks:
                logger.info("[RETRACE] No factual chunks generated for incident '%s'", incident_id)
                return {
                    "incident_id": incident_id,
                    "evidence_processed": total_evidence_processed,
                    "chunks_indexed": 0,
                    "collection": settings.QDRANT_COLLECTION,
                    "status": "synchronized",
                }

            # 4. Generate embeddings
            texts = [c.text for c in chunks]
            embeddings = self.embedding_provider.embed_texts(texts)

            # 5. Ensure target collection
            self.vector_repo.ensure_collection()

            # 6. Reconcile: delete prior points strictly for THIS incident
            self.vector_repo.delete_incident_vectors(incident_id)

            # 7. Upsert deterministic points
            upserted_count = self.vector_repo.upsert_chunks(chunks, embeddings)

            logger.info(
                "[RETRACE] Successfully synchronized %d chunks for incident '%s'",
                upserted_count,
                incident_id,
            )

            return {
                "incident_id": incident_id,
                "evidence_processed": total_evidence_processed,
                "chunks_indexed": upserted_count,
                "collection": settings.QDRANT_COLLECTION,
                "status": "synchronized",
            }

        except EmbeddingProviderError as e:
            logger.error("[RETRACE] Embedding provider error during sync: %s", e.message)
            raise VectorServiceError(f"Embedding failure: {e.message}", status_code=e.status_code)
        except ValueError as e:
            logger.error("[RETRACE] Configuration error during vector sync: %s", str(e))
            raise VectorServiceError(str(e), status_code=400)
        except VectorServiceError:
            raise
        except Exception as e:
            logger.exception("[RETRACE] Unexpected error during vector sync: %s", type(e).__name__)
            raise VectorServiceError(
                f"Failed to synchronize incident vectors: {type(e).__name__}",
                status_code=500,
            )

    def semantic_search(
        self,
        incident_id: str,
        query: str,
        top_k: int = 8,
        asset_id: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute incident-scoped semantic similarity search."""
        if not incident_id or not incident_id.strip():
            raise VectorServiceError("A valid incident_id is required.", status_code=400)

        incident = incident_service.get_incident_by_id(incident_id)
        if not incident:
            raise VectorServiceError(f"Incident '{incident_id}' not found.", status_code=404)

        if not query or not query.strip():
            raise VectorServiceError("Search query must not be empty.", status_code=400)

        if len(query) > 1000:
            raise VectorServiceError("Query exceeds maximum allowable length of 1000 characters.", status_code=400)

        # Enforce top_k constraints: default 8, capped at 20
        bounded_top_k = min(max(1, top_k), 20)

        try:
            # Generate query embedding
            query_embedding = self.embedding_provider.embed_query(query)

            # Retrieve from vector repository
            raw_results = self.vector_repo.semantic_search(
                incident_id=incident_id,
                query_embedding=query_embedding,
                top_k=bounded_top_k,
                asset_id=asset_id,
                source_type=source_type,
            )

            results: List[Dict[str, Any]] = []
            for chunk, score in raw_results:
                if not is_evidence_retrieval_eligible(chunk):
                    continue
                results.append(
                    {
                        "similarity_score": round(score, 4),
                        "evidence_id": chunk.evidence_id,
                        "chunk_id": chunk.chunk_id,
                        "asset_id": chunk.asset_id,
                        "source_type": chunk.source_type,
                        "filename": chunk.filename,
                        "text": chunk.text,
                        "timestamp": chunk.timestamp,
                        "provenance": chunk.provenance,
                    }
                )

            return {
                "incident_id": incident_id,
                "query": query,
                "results": results,
            }

        except EmbeddingProviderError as e:
            logger.error("[RETRACE] Embedding provider error during search: %s", e.message)
            raise VectorServiceError(f"Embedding failure: {e.message}", status_code=e.status_code)
        except VectorServiceError:
            raise
        except Exception as e:
            logger.exception("[RETRACE] Unexpected error during semantic search: %s", type(e).__name__)
            raise VectorServiceError(
                f"Failed to execute semantic search: {type(e).__name__}",
                status_code=500,
            )


# Singleton and dependency injection hooks
_vector_service_instance: Optional[VectorIndexService] = None


def get_vector_index_service() -> VectorIndexService:
    """Retrieve the singleton VectorIndexService."""
    global _vector_service_instance
    if _vector_service_instance is not None:
        return _vector_service_instance

    _vector_service_instance = VectorIndexService()
    return _vector_service_instance


def set_vector_index_service(service: Optional[VectorIndexService]) -> None:
    """Inject a custom or mock VectorIndexService for testing."""
    global _vector_service_instance
    _vector_service_instance = service
