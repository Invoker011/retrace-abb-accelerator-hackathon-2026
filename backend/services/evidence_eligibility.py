"""Evidence retrieval eligibility service for RETRACE.

Provides explicit, centralized rules for determining whether evidence artifacts are
eligible for investigation retrieval (semantic vector search, keyword search,
and fused hybrid retrieval), while preserving complete data provenance and raw storage
in PostgreSQL, GCS, and Neo4j.
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("retrace.eligibility")

# Substrings indicating automated infrastructure verification or test uploads
TEST_ARTIFACT_DESCRIPTIONS = (
    "verification upload",
    "persistence verification",
    "infrastructure verification",
    "test upload",
    "test artifact",
)

TEST_ARTIFACT_FILENAMES = (
    "persistence_test",
    "test_artifact",
    "verify_persistence",
)


def is_evidence_retrieval_eligible(evidence: Any) -> bool:
    """Determine whether an evidence artifact is eligible for investigation retrieval.

    Rules:
    1. Synthetic baseline evidence (EVD-001 through EVD-006) is always eligible by default.
    2. Any evidence explicitly flagged with `retrieval_eligible=False` or `retrievalEligible=False`
       is excluded from retrieval.
    3. Any evidence with metadata specifying `retrieval_eligible=False` or
       `use_type` / `environment` in ('test', 'verification', 'benchmark') is excluded.
    4. Any upload whose description or filename denotes a persistence/infrastructure
       verification upload is excluded from investigation retrieval.
    5. Legitimate operational uploaded evidence remains fully eligible.
    6. Raw storage in PostgreSQL and GCS is NEVER affected by this predicate.
    """
    if evidence is None:
        return False

    # 1. Check explicit top-level attribute (Pydantic models, objects)
    if hasattr(evidence, "retrieval_eligible"):
        val = getattr(evidence, "retrieval_eligible")
        if val is False:
            return False
    if hasattr(evidence, "retrievalEligible"):
        val = getattr(evidence, "retrievalEligible")
        if val is False:
            return False

    # Check dictionary keys if dict
    if isinstance(evidence, dict):
        if evidence.get("retrieval_eligible") is False:
            return False
        if evidence.get("retrievalEligible") is False:
            return False

    # 2. Check metadata dictionary
    meta = getattr(evidence, "metadata", None)
    if meta is None and isinstance(evidence, dict):
        meta = evidence.get("metadata")

    if isinstance(meta, dict):
        if meta.get("retrieval_eligible") is False or meta.get("retrievalEligible") is False:
            return False
        use_type = str(meta.get("use_type") or meta.get("useType") or "").strip().lower()
        if use_type in ("test", "verification", "benchmark", "infra_test"):
            return False
        env = str(meta.get("environment") or "").strip().lower()
        if env in ("test", "verification"):
            return False

    # 3. Check provenance dictionary (e.g. from EvidenceChunk or fused search result)
    prov = getattr(evidence, "provenance", None)
    if prov is None and isinstance(evidence, dict):
        prov = evidence.get("provenance")

    if isinstance(prov, dict):
        if prov.get("retrieval_eligible") is False or prov.get("retrievalEligible") is False:
            return False
        prov_use_type = str(prov.get("use_type") or prov.get("useType") or "").strip().lower()
        if prov_use_type in ("test", "verification", "benchmark", "infra_test"):
            return False
        prov_meta = prov.get("metadata")
        if isinstance(prov_meta, dict):
            if prov_meta.get("retrieval_eligible") is False or prov_meta.get("retrievalEligible") is False:
                return False
            p_use = str(prov_meta.get("use_type") or prov_meta.get("useType") or "").strip().lower()
            if p_use in ("test", "verification", "benchmark", "infra_test"):
                return False

    # 4. Check description for verification/test upload markers
    desc = ""
    if hasattr(evidence, "description"):
        desc = getattr(evidence, "description") or ""
    elif isinstance(evidence, dict):
        desc = evidence.get("description") or ""
    desc_lower = str(desc).strip().lower()

    if any(marker in desc_lower for marker in TEST_ARTIFACT_DESCRIPTIONS):
        return False

    # 5. Check filename for test artifact markers
    fname = ""
    if hasattr(evidence, "original_filename"):
        fname = getattr(evidence, "original_filename") or ""
    elif hasattr(evidence, "filename"):
        fname = getattr(evidence, "filename") or ""
    elif isinstance(evidence, dict):
        fname = evidence.get("original_filename") or evidence.get("filename") or ""
    fname_lower = str(fname).strip().lower()

    if any(marker in fname_lower for marker in TEST_ARTIFACT_FILENAMES):
        return False

    # By default, factual industrial evidence is eligible
    return True
