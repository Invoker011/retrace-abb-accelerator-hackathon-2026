"""Vector repository layer for RETRACE evidence retrieval.

Provides:
- EvidenceVectorRepository: Abstract interface
- QdrantEvidenceVectorRepository: Production implementation using QdrantClient
- InMemoryEvidenceVectorRepository: Deterministic in-memory repository for unit tests and local dev
"""
import math
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from backend.core.config import settings
from backend.services.upload_service import CANONICAL_SOURCE_TYPES
from backend.vector.models import EvidenceChunk
from backend.vector.client import (
    HAS_QDRANT,
    get_qdrant_client,
    ensure_collection as client_ensure_collection,
    check_qdrant_health,
)

logger = logging.getLogger("retrace.vector")

if HAS_QDRANT:
    from qdrant_client.http import models as qmodels
else:
    qmodels = None  # type: ignore


class EvidenceVectorRepository(ABC):
    """Abstract interface for evidence vector storage and similarity retrieval."""

    @abstractmethod
    def ensure_collection(self) -> bool:
        """Ensure collection exists and is configured for 768-dim COSINE vectors."""
        pass

    @abstractmethod
    def upsert_chunks(self, chunks: List[EvidenceChunk], embeddings: List[List[float]]) -> int:
        """Upsert evidence chunks and their embeddings into the vector store."""
        pass

    @abstractmethod
    def delete_incident_vectors(self, incident_id: str) -> int:
        """Remove all RETRACE-managed points belonging strictly to the requested incident."""
        pass

    @abstractmethod
    def semantic_search(
        self,
        incident_id: str,
        query_embedding: List[float],
        top_k: int = 8,
        asset_id: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> List[Tuple[EvidenceChunk, float]]:
        """Perform cosine similarity retrieval filtered by incident_id and optional asset/source."""
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Perform non-mutating health probe."""
        pass


class QdrantEvidenceVectorRepository(EvidenceVectorRepository):
    """Production vector repository utilizing Qdrant."""

    def __init__(
        self,
        collection_name: Optional[str] = None,
        vector_size: Optional[int] = None,
        client: Optional[Any] = None,
    ):
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.vector_size = vector_size or settings.QDRANT_VECTOR_SIZE
        self._custom_client = client

    @property
    def client(self) -> Any:
        if self._custom_client is not None:
            return self._custom_client
        cli = get_qdrant_client()
        if cli is None:
            raise RuntimeError(
                "Qdrant client is not available or not configured. Ensure QDRANT_URL is set."
            )
        return cli

    def ensure_collection(self) -> bool:
        return client_ensure_collection(
            client=self.client,
            collection_name=self.collection_name,
            vector_size=self.vector_size,
            distance_str="COSINE",
        )

    def upsert_chunks(self, chunks: List[EvidenceChunk], embeddings: List[List[float]]) -> int:
        if not chunks:
            return 0
        if len(chunks) != len(embeddings):
            raise ValueError("Count of evidence chunks must match count of embeddings.")

        self.ensure_collection()

        points = [
            qmodels.PointStruct(
                id=chunk.point_id,
                vector=emb,
                payload=chunk.to_payload(),
            )
            for chunk, emb in zip(chunks, embeddings)
        ]

        # Batch upsert in sizes of 64
        batch_size = 64
        total_upserted = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
                wait=True,
            )
            total_upserted += len(batch)

        logger.info(
            "[RETRACE] Successfully upserted %d deterministic points into Qdrant collection '%s'",
            total_upserted,
            self.collection_name,
        )
        return total_upserted

    def delete_incident_vectors(self, incident_id: str) -> int:
        """Tightly scoped incident deletion: removes ONLY points where managed_by=retrace and incident_id matches."""
        if not incident_id or not incident_id.strip():
            raise ValueError("Valid incident_id required for vector deletion.")

        if not self.client.collection_exists(self.collection_name):
            return 0

        # Build strict filter: managed_by == "retrace" AND incident_id == incident_id
        strict_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="managed_by",
                    match=qmodels.MatchValue(value="retrace"),
                ),
                qmodels.FieldCondition(
                    key="incident_id",
                    match=qmodels.MatchValue(value=incident_id),
                ),
            ]
        )

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.FilterSelector(filter=strict_filter),
            wait=True,
        )
        logger.info(
            "[RETRACE] Reconciled / deleted RETRACE-managed points for incident '%s' from collection '%s'",
            incident_id,
            self.collection_name,
        )
        return 1

    def semantic_search(
        self,
        incident_id: str,
        query_embedding: List[float],
        top_k: int = 8,
        asset_id: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> List[Tuple[EvidenceChunk, float]]:
        """Search Qdrant using query_points with incident and asset filtering."""
        if not incident_id or not incident_id.strip():
            raise ValueError("Incident ID is required for scoped semantic search.")

        self.ensure_collection()

        must_conditions: List[Any] = [
            qmodels.FieldCondition(
                key="managed_by",
                match=qmodels.MatchValue(value="retrace"),
            ),
            qmodels.FieldCondition(
                key="incident_id",
                match=qmodels.MatchValue(value=incident_id),
            ),
        ]

        if asset_id and str(asset_id).strip():
            must_conditions.append(
                qmodels.FieldCondition(
                    key="asset_id",
                    match=qmodels.MatchValue(value=str(asset_id).strip()),
                )
            )

        if source_type and str(source_type).strip():
            st = str(source_type).strip()
            alt_st = CANONICAL_SOURCE_TYPES.get(st)
            candidates = [st] if not alt_st else [st, alt_st]
            if len(candidates) > 1:
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="source_type",
                        match=qmodels.MatchAny(any=candidates),
                    )
                )
            else:
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="source_type",
                        match=qmodels.MatchValue(value=st),
                    )
                )

        search_filter = qmodels.Filter(must=must_conditions)

        # Prefer query_points, fall back to search if query_points not present in client version
        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=search_filter,
                limit=top_k,
                with_payload=True,
            )
            hits = response.points
        else:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=top_k,
                with_payload=True,
            )

        results: List[Tuple[EvidenceChunk, float]] = []
        for hit in hits:
            score = float(getattr(hit, "score", 0.0))
            payload = getattr(hit, "payload", {}) or {}
            chunk = EvidenceChunk.from_payload(payload, point_id=str(hit.id))
            results.append((chunk, score))

        return results

    def health(self) -> Dict[str, Any]:
        return check_qdrant_health()


class InMemoryEvidenceVectorRepository(EvidenceVectorRepository):
    """Deterministic in-memory vector repository for unit tests and local offline development."""

    def __init__(
        self,
        collection_name: Optional[str] = None,
        vector_size: int = 768,
        distance: str = "COSINE",
    ):
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.vector_size = vector_size
        self.distance = distance
        self._collections: Dict[str, Dict[str, Any]] = {}
        # Storage keyed by point_id: { "chunk": EvidenceChunk, "vector": List[float] }
        self._store: Dict[str, Dict[str, Any]] = {}

    def ensure_collection(self) -> bool:
        if self.collection_name not in self._collections:
            self._collections[self.collection_name] = {
                "vector_size": self.vector_size,
                "distance": self.distance,
            }
            return True

        # Existing collection: verify configuration
        conf = self._collections[self.collection_name]
        if conf["vector_size"] != self.vector_size:
            raise ValueError(
                f"Collection '{self.collection_name}' vector dimension mismatch: "
                f"expected {self.vector_size}, found {conf['vector_size']}"
            )
        if conf["distance"] != self.distance:
            raise ValueError(
                f"Collection '{self.collection_name}' distance mismatch: "
                f"expected {self.distance}, found {conf['distance']}"
            )
        return False

    def upsert_chunks(self, chunks: List[EvidenceChunk], embeddings: List[List[float]]) -> int:
        self.ensure_collection()
        for chunk, emb in zip(chunks, embeddings):
            self._store[chunk.point_id] = {
                "chunk": chunk,
                "vector": emb,
            }
        return len(chunks)

    def delete_incident_vectors(self, incident_id: str) -> int:
        to_delete = [
            pid
            for pid, item in self._store.items()
            if item["chunk"].managed_by == "retrace" and item["chunk"].incident_id == incident_id
        ]
        for pid in to_delete:
            del self._store[pid]
        return len(to_delete)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return max(-1.0, min(1.0, dot / (norm_a * norm_b)))

    def semantic_search(
        self,
        incident_id: str,
        query_embedding: List[float],
        top_k: int = 8,
        asset_id: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> List[Tuple[EvidenceChunk, float]]:
        self.ensure_collection()

        candidates: List[Tuple[EvidenceChunk, float]] = []

        valid_source_types = set()
        if source_type:
            st = source_type.strip()
            valid_source_types.add(st)
            alt = CANONICAL_SOURCE_TYPES.get(st)
            if alt:
                valid_source_types.add(alt)

        for item in self._store.values():
            chunk: EvidenceChunk = item["chunk"]
            vector: List[float] = item["vector"]

            # 1. ALWAYS filter by managed_by=retrace and incident_id
            if chunk.managed_by != "retrace" or chunk.incident_id != incident_id:
                continue

            # 2. Optional asset filter
            if asset_id and chunk.asset_id != asset_id:
                continue

            # 3. Optional source type filter
            if valid_source_types and chunk.source_type not in valid_source_types:
                continue

            sim = self._cosine_similarity(query_embedding, vector)
            candidates.append((chunk, sim))

        # Sort by similarity descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]

    def health(self) -> Dict[str, Any]:
        return {
            "vector": "connected",
            "provider": "in_memory",
            "collection": self.collection_name,
        }
