"""Deterministic Keyword and Exact Evidence Search Service for RETRACE.

Provides factual lexical retrieval over incident evidence chunks without invoking external
indexing services or fabricating text content.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.schemas.evidence import Evidence
from backend.schemas.upload import UploadedEvidence
from backend.services.incident_service import incident_service
from backend.repositories.uploaded_evidence_repository import (
    UploadedEvidenceRepositoryInterface,
    get_uploaded_evidence_repository,
)
from backend.vector.chunking import EvidenceChunkingService
from backend.vector.models import EvidenceChunk
from backend.services.identifier_recognition import identifier_recognition_service

logger = logging.getLogger(__name__)

# Standard stop words to ignore during lexical token overlap
STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "up", "about", "into", "over", "after", "before",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "what", "which", "who", "whom", "this", "that", "these",
    "those", "there", "where", "when", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "can", "will", "just", "should", "now",
}

# Tokenizer pattern matching industrial terms with hyphens (e.g. VFD-204, ISO-10816)
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


class KeywordEvidenceSearchService:
    """Deterministic lexical retrieval engine for RETRACE factual evidence."""

    def __init__(
        self,
        chunking_service: Optional[EvidenceChunkingService] = None,
        upload_repo: Optional[UploadedEvidenceRepositoryInterface] = None,
    ):
        self._chunking_service = chunking_service or EvidenceChunkingService()
        self._upload_repo = upload_repo

    @property
    def chunking_service(self) -> EvidenceChunkingService:
        return self._chunking_service

    @property
    def upload_repo(self) -> UploadedEvidenceRepositoryInterface:
        if self._upload_repo is not None:
            return self._upload_repo
        return get_uploaded_evidence_repository()

    def _tokenize(self, text: str) -> List[str]:
        """Extract alphanumeric and hyphenated tokens from text."""
        if not text:
            return []
        raw_tokens = TOKEN_PATTERN.findall(text.lower())
        return [t for t in raw_tokens if t and (t not in STOP_WORDS or "-" in t)]

    def get_incident_chunks(self, incident_id: str) -> List[EvidenceChunk]:
        """Load and deterministically chunk all factual evidence for the incident."""
        synthetic_evidence: List[Evidence] = incident_service.get_incident_evidence(incident_id)

        uploaded_records: List[UploadedEvidence] = []
        try:
            uploaded_records = self.upload_repo.get_by_incident(incident_id)
        except Exception as e:
            logger.warning("[RETRACE] Could not load uploaded evidence for keyword search: %s", type(e).__name__)

        return self.chunking_service.build_chunks_for_incident(
            incident_id=incident_id,
            synthetic_evidence=synthetic_evidence,
            uploaded_evidence=uploaded_records,
        )

    def search(
        self,
        incident_id: str,
        query: str,
        top_k: int = 8,
        asset_id: Optional[str] = None,
        source_type: Optional[str] = None,
        recognized_identifiers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform deterministic lexical scoring over incident evidence chunks.

        Scoring Rules:
        - Exact Identifier Match (+50.0 for direct asset/evidence match, +30.0 for text mention)
        - Exact Multi-word Phrase Match (+25.0 in text, +15.0 in filename)
        - Asset Tag Match (+20.0)
        - Source Type Relevance (+10.0)
        - Token Overlap / Term Frequency weighted by relevance
        """
        if not query or not query.strip():
            return []

        all_chunks = self.get_incident_chunks(incident_id)
        if not all_chunks:
            return []

        # 1. Apply asset_id and source_type hard filters
        filtered_chunks: List[EvidenceChunk] = []
        target_asset = asset_id.strip().upper() if asset_id and asset_id.strip() else None
        target_source = source_type.strip().lower() if source_type and source_type.strip() else None

        for chunk in all_chunks:
            if target_asset:
                chunk_asset = (chunk.asset_id or "").strip().upper()
                if chunk_asset != target_asset:
                    continue
            if target_source:
                chunk_source = (chunk.source_type or "").strip().lower()
                if target_source not in chunk_source and chunk_source not in target_source:
                    continue
            filtered_chunks.append(chunk)

        if not filtered_chunks:
            return []

        # 2. Prepare query tokens and recognized identifiers
        query_clean = query.strip()
        query_lower = query_clean.lower()
        query_tokens = self._tokenize(query_clean)

        if recognized_identifiers is None:
            recognized_identifiers = identifier_recognition_service.extract_identifiers(query_clean)
        clean_identifiers = [i.upper() for i in recognized_identifiers]

        # 3. Score each chunk deterministically
        scored_results: List[Tuple[float, EvidenceChunk, bool]] = []

        from backend.services.evidence_eligibility import is_evidence_retrieval_eligible
        for chunk in filtered_chunks:
            if not is_evidence_retrieval_eligible(chunk):
                continue
            score = 0.0
            chunk_text_lower = chunk.text.lower()
            chunk_filename_lower = chunk.filename.lower()
            chunk_asset_upper = (chunk.asset_id or "").upper()
            chunk_ev_upper = (chunk.evidence_id or "").upper()
            chunk_source_lower = chunk.source_type.lower()
            has_identifier_match = False

            # A. Strong boost for recognized identifier matches
            for ident in clean_identifiers:
                ident_lower = ident.lower()
                # Direct asset match
                if ident == chunk_asset_upper:
                    score += 50.0
                    has_identifier_match = True
                # Direct evidence ID match
                elif ident == chunk_ev_upper:
                    score += 60.0
                    has_identifier_match = True
                # Text mention of identifier
                elif ident_lower in chunk_text_lower:
                    score += 30.0
                    has_identifier_match = True
                elif ident_lower in chunk_filename_lower:
                    score += 30.0
                    has_identifier_match = True

            # B. Exact phrase match (if query has multiple meaningful words)
            meaningful_query = " ".join(query_tokens)
            if len(query_tokens) >= 2 and meaningful_query in chunk_text_lower:
                score += 25.0
            elif len(query_tokens) >= 2 and query_lower in chunk_text_lower:
                score += 30.0

            # C. Filename match
            for qt in query_tokens:
                if qt in chunk_filename_lower:
                    score += 8.0

            # D. Source type relevance match
            for qt in query_tokens:
                if qt in chunk_source_lower:
                    score += 6.0

            # E. Token overlap and frequency
            matched_token_count = 0
            for qt in query_tokens:
                # Count occurrences in chunk text (capped at 5 to avoid saturation)
                count = chunk_text_lower.count(qt)
                if count > 0:
                    matched_token_count += 1
                    score += min(count, 5) * 2.0

            # Proportional coverage bonus
            if query_tokens:
                coverage = matched_token_count / len(query_tokens)
                score += coverage * 12.0

            # Only retain chunks with a positive score
            if score > 0.0:
                scored_results.append((score, chunk, has_identifier_match))

        # 4. Sort deterministically: highest score first, breaking ties by (chunk_id, evidence_id)
        scored_results.sort(
            key=lambda item: (-item[0], item[1].chunk_id, item[1].evidence_id)
        )

        # 5. Format results with keyword_rank and keyword_score
        formatted: List[Dict[str, Any]] = []
        bounded_top_k = min(max(1, top_k), 20)

        for rank_idx, (score, chunk, matched_id) in enumerate(scored_results[:bounded_top_k], start=1):
            formatted.append(
                {
                    "keyword_rank": rank_idx,
                    "keyword_score": round(score, 4),
                    "evidence_id": chunk.evidence_id,
                    "chunk_id": chunk.chunk_id,
                    "asset_id": chunk.asset_id,
                    "source_type": chunk.source_type,
                    "filename": chunk.filename,
                    "text": chunk.text,
                    "timestamp": chunk.timestamp,
                    "provenance": chunk.provenance,
                    "has_identifier_match": matched_id,
                }
            )

        return formatted


# Singleton instance
keyword_evidence_search_service = KeywordEvidenceSearchService()
