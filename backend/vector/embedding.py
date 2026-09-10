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
    from google.genai.errors import APIError, ClientError
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    genai = None  # type: ignore
    genai_types = None  # type: ignore
    APIError = Exception  # type: ignore
    ClientError = Exception  # type: ignore

DOCUMENT_INSTRUCTION = "Represent this industrial maintenance evidence for semantic retrieval."
QUERY_INSTRUCTION = "Represent this industrial maintenance troubleshooting question for retrieving relevant evidence."


def _sanitize_error_message(msg: Any) -> str:
    """Sanitize error message to prevent leaking secrets, credentials, or evidence text."""
    if not msg:
        return "No error details provided"
    import re
    cleaned = str(msg).strip().replace("\n", " ").replace("\r", " ")
    # Redact credentials, tokens, and authorization values
    cleaned = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1[REDACTED]", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(key[=:]\s*)[A-Za-z0-9_\-]+", r"\1[REDACTED]", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(token[=:]\s*)[A-Za-z0-9_\-]+", r"\1[REDACTED]", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(password[=:]\s*)[^\s,]+", r"\1[REDACTED]", cleaned, flags=re.IGNORECASE)
    # Truncate to safe length to avoid leaking full body payloads
    if len(cleaned) > 300:
        cleaned = cleaned[:300] + "... [truncated]"
    return cleaned


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
            status_code = getattr(e, "code", None) or getattr(e, "status_code", None)
            raw_msg = getattr(e, "message", None) or str(e)
            sanitized_msg = _sanitize_error_message(raw_msg)
            logger.error(
                "[RETRACE] Vertex AI client initialization error: status_code=%s, error_message='%s', project='%s', location='%s'",
                status_code,
                sanitized_msg,
                self.project,
                self.location,
            )
            raise EmbeddingProviderError(
                f"Vertex AI embedding provider initialization failed: {type(e).__name__}"
            )

    def embed_texts(self, texts: List[str], instruction: Optional[str] = None) -> List[List[float]]:
        if not texts:
            return []

        client = self._get_client()
        inst = instruction or DOCUMENT_INSTRUCTION
        embeddings: List[List[float]] = []

        # Embed each chunk individually to ensure 1:1 chunk-to-embedding mapping
        # and prevent gemini-embedding-2 from treating a list of strings as one multi-part Content
        for text in texts:
            formatted_text = f"{inst}\n{text}" if inst else text
            try:
                if genai_types and hasattr(genai_types, "EmbedContentConfig"):
                    config = genai_types.EmbedContentConfig(
                        output_dimensionality=self.dimension,
                    )
                else:
                    config = {"output_dimensionality": self.dimension}

                response = client.models.embed_content(
                    model=self.model,
                    contents=formatted_text,
                    config=config,
                )

                # Extract embedding values
                values = None
                if hasattr(response, "embedding") and response.embedding:
                    values = getattr(response.embedding, "values", response.embedding)
                elif hasattr(response, "embeddings") and response.embeddings:
                    first = response.embeddings[0]
                    values = getattr(first, "values", first)

                if values is None:
                    raise ValueError("Unexpected response format: no embedding values returned from model")

                embeddings.append(list(values))

            except Exception as e:
                status_code = getattr(e, "code", None) or getattr(e, "status_code", None)
                raw_msg = getattr(e, "message", None) or str(e)
                sanitized_msg = _sanitize_error_message(raw_msg)

                logger.error(
                    "[RETRACE] Vertex AI text embedding ClientError: status_code=%s, error_message='%s', model='%s', location='%s', dimension=%d",
                    status_code,
                    sanitized_msg,
                    self.model,
                    self.location,
                    self.dimension,
                )
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
