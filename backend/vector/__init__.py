"""RETRACE Qdrant Vector Retrieval Layer."""
from backend.vector.models import (
    EvidenceChunk,
    SemanticSearchRequest,
    SemanticSearchResultItem,
    SemanticSearchResponse,
    VectorSyncResponse,
    generate_deterministic_point_id,
)
from backend.vector.client import (
    get_qdrant_client,
    close_qdrant_client,
    check_qdrant_health,
    ensure_collection,
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
from backend.vector.service import (
    VectorIndexService,
    VectorServiceError,
    get_vector_index_service,
    set_vector_index_service,
)

__all__ = [
    "EvidenceChunk",
    "SemanticSearchRequest",
    "SemanticSearchResultItem",
    "SemanticSearchResponse",
    "VectorSyncResponse",
    "generate_deterministic_point_id",
    "get_qdrant_client",
    "close_qdrant_client",
    "check_qdrant_health",
    "ensure_collection",
    "EmbeddingProvider",
    "GeminiEmbeddingProvider",
    "FakeEmbeddingProvider",
    "EmbeddingProviderError",
    "EvidenceChunkingService",
    "EvidenceVectorRepository",
    "QdrantEvidenceVectorRepository",
    "InMemoryEvidenceVectorRepository",
    "VectorIndexService",
    "VectorServiceError",
    "get_vector_index_service",
    "set_vector_index_service",
]
