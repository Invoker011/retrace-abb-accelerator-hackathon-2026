"""Evidence chunking service for RETRACE.

Deterministically transforms synthetic baseline evidence and uploaded evidence artifacts
into factual EvidenceChunks without inventing observations, timestamps, or captions.
"""
import re
import hashlib
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("retrace.chunking")

from backend.schemas.evidence import Evidence
from backend.schemas.upload import UploadedEvidence
from backend.vector.models import EvidenceChunk, generate_deterministic_point_id

PROTECTED_IDENTIFIERS = {"VFD-204", "M-204", "P-204", "PLC-204"}


def split_text_deterministically(
    text: str,
    max_chunk_chars: int = 800,
    overlap_chars: int = 80,
) -> List[str]:
    """Split text deterministically into manageable chunks with safe boundary detection.

    Avoids splitting industrial asset identifiers like VFD-204, M-204, P-204, PLC-204.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    if len(clean_text) <= max_chunk_chars:
        return [clean_text]

    chunks: List[str] = []
    start = 0
    text_len = len(clean_text)

    while start < text_len:
        end = min(start + max_chunk_chars, text_len)
        if end < text_len:
            # Look backwards from end for natural split points (\n\n, \n, sentence period, space)
            split_at = -1
            candidate_window = clean_text[start:end]

            for delimiter in ["\n\n", "\n", ". ", "; ", ", ", " "]:
                last_pos = candidate_window.rfind(delimiter)
                if last_pos > int(max_chunk_chars * 0.6):
                    split_at = start + last_pos + len(delimiter)
                    break

            if split_at != -1:
                # Check if split_at divides any protected identifier
                for ident in PROTECTED_IDENTIFIERS:
                    ident_idx = clean_text.find(ident, max(0, split_at - len(ident)), split_at + len(ident))
                    if ident_idx != -1 and ident_idx < split_at < ident_idx + len(ident):
                        # Avoid splitting the identifier: shift past it
                        split_at = ident_idx + len(ident)
                        break
                end = split_at

        chunk_slice = clean_text[start:end].strip()
        if chunk_slice:
            chunks.append(chunk_slice)

        if end >= text_len:
            break

        # Move forward with deterministic overlap
        start = max(end - overlap_chars, start + 1)

    return chunks


class EvidenceChunkingService:
    """Orchestrates factual chunking across synthetic and uploaded evidence sources."""

    def chunk_synthetic_evidence(
        self,
        evidence: Evidence,
        incident_id: str,
    ) -> List[EvidenceChunk]:
        """Convert synthetic baseline evidence into factual EvidenceChunks.

        Uses only factual content actually present in the evidence object (rawContent,
        previewRows, extractedEvent). Does not manufacture observations.
        """
        from backend.services.evidence_eligibility import is_evidence_retrieval_eligible
        if not is_evidence_retrieval_eligible(evidence):
            return []

        chunks: List[EvidenceChunk] = []
        ev_id = evidence.id
        asset_id = evidence.asset_id
        source_type = evidence.source_type
        filename = evidence.filename
        content_type = getattr(evidence, "format", "text")
        if content_type == "csv":
            mime_type = "text/csv"
            modality = "tabular"
        elif content_type == "pdf":
            mime_type = "application/pdf"
            modality = "document"
        else:
            mime_type = "text/plain"
            modality = "text"

        provenance = {
            "source": evidence.source,
            "original_reference": evidence.original_reference,
            "normalized_timestamp": evidence.normalized_timestamp,
            "confidence": getattr(evidence, "confidence", None),
            "metadata": evidence.metadata or {},
        }
        storage_uri = f"synthetic://incidents/{incident_id}/evidence/{ev_id}/{filename}"
        sha256_hash = hashlib.sha256(f"{incident_id}:{ev_id}:{filename}".encode("utf-8")).hexdigest()

        raw_content = getattr(evidence, "raw_content", None)
        preview_rows = getattr(evidence, "preview_rows", None)
        extracted_content = evidence.extracted_content or ""

        # Strategy 1: Tabular data with preview rows
        if preview_rows and isinstance(preview_rows, list) and len(preview_rows) > 0:
            header_prefix = (
                f"Source: {evidence.source} | Asset: {asset_id} | File: {filename}\n"
                f"Extracted Event: {extracted_content}\n"
                f"Telemetry / Log Preview Rows ({len(preview_rows)} entries):\n"
            )
            rows_formatted = []
            for idx, r in enumerate(preview_rows):
                items = " | ".join(f"{k}: {v}" for k, v in r.items())
                rows_formatted.append(f"Row {idx + 1}: {items}")
            full_table_text = header_prefix + "\n".join(rows_formatted)

            text_chunks = split_text_deterministically(full_table_text, max_chunk_chars=900)
            for c_idx, c_text in enumerate(text_chunks):
                point_id = generate_deterministic_point_id(incident_id, ev_id, c_idx)
                chunks.append(
                    EvidenceChunk(
                        point_id=point_id,
                        incident_id=incident_id,
                        evidence_id=ev_id,
                        chunk_id=f"{ev_id}-chk-{c_idx}",
                        chunk_index=c_idx,
                        asset_id=asset_id,
                        source_type=source_type,
                        filename=filename,
                        content_type=mime_type,
                        modality="tabular",
                        text=c_text,
                        storage_uri=storage_uri,
                        sha256_hash=sha256_hash,
                        provenance=provenance,
                        managed_by="retrace",
                        row_start=1,
                        row_end=len(preview_rows),
                        timestamp=evidence.normalized_timestamp,
                    )
                )

        # Strategy 2: Textual / document with raw content
        elif raw_content and str(raw_content).strip():
            header = f"Source: {evidence.source} | Asset: {asset_id} | File: {filename}\n"
            combined_text = header + str(raw_content).strip()
            text_chunks = split_text_deterministically(combined_text, max_chunk_chars=800)

            page_num = evidence.metadata.get("page") if evidence.metadata else None

            for c_idx, c_text in enumerate(text_chunks):
                point_id = generate_deterministic_point_id(incident_id, ev_id, c_idx)
                chunks.append(
                    EvidenceChunk(
                        point_id=point_id,
                        incident_id=incident_id,
                        evidence_id=ev_id,
                        chunk_id=f"{ev_id}-chk-{c_idx}",
                        chunk_index=c_idx,
                        asset_id=asset_id,
                        source_type=source_type,
                        filename=filename,
                        content_type=mime_type,
                        modality=modality,
                        text=c_text,
                        storage_uri=storage_uri,
                        sha256_hash=sha256_hash,
                        provenance=provenance,
                        managed_by="retrace",
                        page_number=page_num,
                        timestamp=evidence.normalized_timestamp,
                    )
                )

        # Strategy 3: Extracted event text fallback
        elif extracted_content.strip():
            content_text = (
                f"Source: {evidence.source} | Asset: {asset_id} | File: {filename}\n"
                f"Observed Event: {extracted_content}"
            )
            point_id = generate_deterministic_point_id(incident_id, ev_id, 0)
            chunks.append(
                EvidenceChunk(
                    point_id=point_id,
                    incident_id=incident_id,
                    evidence_id=ev_id,
                    chunk_id=f"{ev_id}-chk-0",
                    chunk_index=0,
                    asset_id=asset_id,
                    source_type=source_type,
                    filename=filename,
                    content_type=mime_type,
                    modality=modality,
                    text=content_text,
                    storage_uri=storage_uri,
                    sha256_hash=sha256_hash,
                    provenance=provenance,
                    managed_by="retrace",
                    timestamp=evidence.normalized_timestamp,
                )
            )

        return chunks

    def chunk_uploaded_evidence(
        self,
        record: UploadedEvidence,
    ) -> List[EvidenceChunk]:
        """Convert a persistent uploaded evidence record into factual EvidenceChunks.

        Reuses actual extracted metadata (preview_text, columns, preview_rows).
        DOES NOT invent text or captions if none was extracted.
        """
        from backend.services.evidence_eligibility import is_evidence_retrieval_eligible
        if not is_evidence_retrieval_eligible(record):
            logger.info("[RETRACE] Skipping chunking for retrieval-ineligible upload '%s'", getattr(record, 'evidence_id', 'unknown'))
            return []

        chunks: List[EvidenceChunk] = []
        ev_id = record.evidence_id
        incident_id = record.incident_id
        asset_id = record.asset_id
        source_type = record.source_type
        filename = record.original_filename
        content_type = record.content_type
        meta = record.metadata or {}

        provenance = {
            "source_type": source_type,
            "uploaded_at": record.uploaded_at,
            "sha256_hash": record.sha256_hash,
            "file_size": record.file_size,
            "metadata": meta,
        }

        # 1. CSV Evidence
        if "csv" in content_type.lower() or meta.get("format") == "csv":
            cols = meta.get("columns", [])
            preview_rows = meta.get("preview_rows", [])
            row_count = meta.get("row_count", len(preview_rows))

            if preview_rows or cols:
                parts = [f"Uploaded CSV File: {filename} | Asset: {asset_id or 'General Skid'}"]
                if record.description:
                    parts.append(f"Description: {record.description}")
                if cols:
                    parts.append(f"Columns: {', '.join(str(c) for c in cols)}")
                if preview_rows:
                    parts.append(f"Sample Records ({len(preview_rows)} of {row_count}):")
                    for r_idx, r in enumerate(preview_rows):
                        row_str = " | ".join(f"{k}: {v}" for k, v in r.items())
                        parts.append(f"Row {r_idx + 1}: {row_str}")

                combined_csv_text = "\n".join(parts)
                text_slices = split_text_deterministically(combined_csv_text, max_chunk_chars=900)
                for c_idx, c_text in enumerate(text_slices):
                    point_id = generate_deterministic_point_id(incident_id, ev_id, c_idx)
                    chunks.append(
                        EvidenceChunk(
                            point_id=point_id,
                            incident_id=incident_id,
                            evidence_id=ev_id,
                            chunk_id=f"{ev_id}-chk-{c_idx}",
                            chunk_index=c_idx,
                            asset_id=asset_id,
                            source_type=source_type,
                            filename=filename,
                            content_type=content_type,
                            modality="tabular",
                            text=c_text,
                            storage_uri=record.storage_uri,
                            sha256_hash=record.sha256_hash,
                            provenance=provenance,
                            managed_by="retrace",
                            row_start=1 if preview_rows else None,
                            row_end=len(preview_rows) if preview_rows else None,
                            timestamp=record.uploaded_at,
                        )
                    )

        # 2. Text Evidence
        elif "text" in content_type.lower() or meta.get("format") == "text":
            preview_text = meta.get("preview_text") or record.description
            if preview_text and str(preview_text).strip():
                header = f"Uploaded Text Note: {filename} | Asset: {asset_id or 'General Skid'}\n"
                full_text = header + str(preview_text).strip()
                text_slices = split_text_deterministically(full_text, max_chunk_chars=800)
                for c_idx, c_text in enumerate(text_slices):
                    point_id = generate_deterministic_point_id(incident_id, ev_id, c_idx)
                    chunks.append(
                        EvidenceChunk(
                            point_id=point_id,
                            incident_id=incident_id,
                            evidence_id=ev_id,
                            chunk_id=f"{ev_id}-chk-{c_idx}",
                            chunk_index=c_idx,
                            asset_id=asset_id,
                            source_type=source_type,
                            filename=filename,
                            content_type=content_type,
                            modality="text",
                            text=c_text,
                            storage_uri=record.storage_uri,
                            sha256_hash=record.sha256_hash,
                            provenance=provenance,
                            managed_by="retrace",
                            timestamp=record.uploaded_at,
                        )
                    )

        # 3. PDF Evidence
        elif "pdf" in content_type.lower() or meta.get("format") == "pdf":
            preview_text = meta.get("preview_text")
            # Strictly do not fabricate text if only page count or header is known
            if preview_text and str(preview_text).strip():
                header = f"Uploaded PDF Manual: {filename} | Asset: {asset_id or 'General Skid'}\n"
                full_text = header + str(preview_text).strip()
                text_slices = split_text_deterministically(full_text, max_chunk_chars=800)
                for c_idx, c_text in enumerate(text_slices):
                    point_id = generate_deterministic_point_id(incident_id, ev_id, c_idx)
                    chunks.append(
                        EvidenceChunk(
                            point_id=point_id,
                            incident_id=incident_id,
                            evidence_id=ev_id,
                            chunk_id=f"{ev_id}-chk-{c_idx}",
                            chunk_index=c_idx,
                            asset_id=asset_id,
                            source_type=source_type,
                            filename=filename,
                            content_type=content_type,
                            modality="document",
                            text=c_text,
                            storage_uri=record.storage_uri,
                            sha256_hash=record.sha256_hash,
                            provenance=provenance,
                            managed_by="retrace",
                            page_number=meta.get("pages"),
                            timestamp=record.uploaded_at,
                        )
                    )
            # If no preview_text extracted: do not invent PDF content

        # 4. Images / Unrecognized:
        # Strictly do not invent captions. Multimodal vision models will handle images in later phases.

        return chunks

    def build_chunks_for_incident(
        self,
        incident_id: str,
        synthetic_evidence: List[Evidence],
        uploaded_evidence: List[UploadedEvidence],
    ) -> List[EvidenceChunk]:
        """Aggregate and deterministically chunk all incident evidence."""
        from backend.services.evidence_eligibility import is_evidence_retrieval_eligible
        all_chunks: List[EvidenceChunk] = []

        for syn in synthetic_evidence:
            if is_evidence_retrieval_eligible(syn):
                all_chunks.extend(self.chunk_synthetic_evidence(syn, incident_id))

        for upl in uploaded_evidence:
            if is_evidence_retrieval_eligible(upl):
                all_chunks.extend(self.chunk_uploaded_evidence(upl))

        return all_chunks
