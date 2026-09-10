"""Embedding provider abstraction and implementations for RETRACE.

Includes:
- EmbeddingProvider: Abstract base interface
- GeminiEmbeddingProvider: Production implementation using Vertex AI (Application Default Credentials)
- FakeEmbeddingProvider: Deterministic 768-dimensional provider for unit testing and offline development
"""
import math
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from backend.core.config import settings

logger = logging.getLogger("retrace.vector")

try:
    from google import genai
    from google.genai import types as genai_types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    genai = None  # type: ignore
    genai_types = None  # type: ignore

DOCUMENT_INSTRUCTION = "Represent this industrial maintenance evidence for semantic retrieval."
QUERY_INSTRUCTION = "Represent this industrial maintenance troubleshooting question for retrieving relevant evidence."


class EmbeddingProviderError(Exception):
    """Exception raised when embedding generation fails."""
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class EmbeddingProvider(ABC):
    """Abstract interface for generating vector embeddings."""

    @abstractmethod
    def embed_texts(self, texts: List[str], instruction: Optional[str] = None) -> List[List[float]]:
        """Embed a list of textual evidence contents."""
        pass

    @abstractmethod
    def embed_query(self, query: str, instruction: Optional[str] = None) -> List[float]:
        """Embed a single search query."""
        pass


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Production embedding provider using Google Cloud Vertex AI and gemini-embedding-2.

    Authenticates via Google Cloud Application Default Credentials (ADC) attached
    to the Cloud Run service account. Never uses or expects hardcoded API keys.
    """

    def __init__(
        self,
        project: Optional[str] = None,
        location: Optional[str] = None,
        model: Optional[str] = None,
        dimension: Optional[int] = None,
    ):
        self.project = project or settings.GOOGLE_CLOUD_PROJECT
        self.location = location or settings.GOOGLE_CLOUD_LOCATION
        self.model = model or settings.EMBEDDING_MODEL
        self.dimension = dimension or settings.EMBEDDING_DIMENSION
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        if not HAS_GENAI:
            raise EmbeddingProviderError(
                "The 'google-genai' SDK is not installed. Ensure backend requirements are satisfied."
            )

        try:
            self._client = genai.Client(
                vertexai=True,
                project=self.project,
                location=self.location,
            )
            return self._client
        except Exception as e:
            logger.warning("[RETRACE] Failed to initialize Vertex AI genai client: %s", type(e).__name__)
            raise EmbeddingProviderError(
                f"Vertex AI embedding provider initialization failed: {type(e).__name__}"
            )

    def embed_texts(self, texts: List[str], instruction: Optional[str] = None) -> List[List[float]]:
        if not texts:
            return []

        client = self._get_client()
        inst = instruction or DOCUMENT_INSTRUCTION
        embeddings: List[List[float]] = []

        # Process in batches of 16 to respect service limits
        batch_size = 16
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                # Format texts with instruction prefix if requested
                formatted_batch = [f"{inst}\n{t}" if inst else t for t in batch]
                
                config_kwargs = {}
                if genai_types and hasattr(genai_types, "EmbedContentConfig"):
                    config = genai_types.EmbedContentConfig(
                        output_dimensionality=self.dimension,
                    )
                    config_kwargs["config"] = config
                else:
                    config_kwargs["config"] = {"output_dimensionality": self.dimension}

                response = client.models.embed_content(
                    model=self.model,
                    contents=formatted_batch,
                    **config_kwargs,
                )

                # Extract embedding values
                if hasattr(response, "embeddings") and response.embeddings:
                    for emb in response.embeddings:
                        values = getattr(emb, "values", None)
                        if values is None and isinstance(emb, list):
                            values = emb
                        embeddings.append(list(values or []))
                elif hasattr(response, "embedding") and response.embedding:
                    values = getattr(response.embedding, "values", None)
                    embeddings.append(list(values or []))
                else:
                    raise ValueError("Unexpected response format from embedding model")

            except Exception as e:
                logger.error("[RETRACE] Vertex AI text embedding error: %s", type(e).__name__)
                raise EmbeddingProviderError(
                    f"Failed to generate evidence embeddings via Vertex AI: {type(e).__name__}"
                )

        return embeddings

    def embed_query(self, query: str, instruction: Optional[str] = None) -> List[float]:
        if not query or not query.strip():
            raise ValueError("Query string must not be empty.")

        inst = instruction or QUERY_INSTRUCTION
        results = self.embed_texts([query], instruction=inst)
        if not results:
            raise EmbeddingProviderError("Failed to produce embedding for query.")
        return results[0]


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic, offline embedding provider for unit tests and local mock verification.

    Always returns normalized float vectors of exact dimension 768.
    Generates reproducible vectors based on cryptographic hashing of input text.
    """

    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    def _generate_vector(self, text: str, salt: str = "") -> List[float]:
        raw_bytes = hashlib.sha256(f"{salt}:{text}".encode("utf-8")).digest()
        vector: List[float] = []

        # Derive 768 deterministic float values from text tokens and byte hash
        words = text.lower().split()
        word_hash = sum(ord(c) for c in "".join(words)) if words else 42

        for dim_idx in range(self.dimension):
            byte_val = raw_bytes[(dim_idx % len(raw_bytes))]
            # Deterministic sinusoidal distribution
            angle = (dim_idx * 0.1337) + (byte_val * 0.05) + ((word_hash % 100) * 0.01)
            val = math.sin(angle)
            vector.append(val)

        # L2 normalize vector so cosine similarity is well-behaved [-1.0, 1.0]
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [round(v / norm, 6) for v in vector]

        assert len(vector) == self.dimension, f"Vector dimension must be exactly {self.dimension}"
        return vector

    def embed_texts(self, texts: List[str], instruction: Optional[str] = None) -> List[List[float]]:
        prefix = instruction or DOCUMENT_INSTRUCTION
        return [self._generate_vector(t, salt=prefix) for t in texts]

    def embed_query(self, query: str, instruction: Optional[str] = None) -> List[float]:
        prefix = instruction or QUERY_INSTRUCTION
        return self._generate_vector(query, salt=prefix)
