"""RETRACE Hybrid Retrieval Service.

Integrates semantic retrieval (Qdrant), deterministic keyword/lexical retrieval,
Reciprocal Rank Fusion (RRF), Neo4j Incident Context Graph expansion, and
chronological temporal sequencing into an evidence-grounded context package.
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.core.config import settings
from backend.schemas.hybrid_search import (
    HybridEvidenceResult,
    HybridSearchResponse,
    TemporalContextItem,
)
from backend.services.incident_service import incident_service
from backend.vector.service import VectorIndexService, VectorServiceError, get_vector_index_service
from backend.services.keyword_search_service import (
    KeywordEvidenceSearchService,
    keyword_evidence_search_service,
)
from backend.services.identifier_recognition import (
    IdentifierRecognitionService,
    identifier_recognition_service,
)
from backend.services.temporal_context_service import (
    TemporalContextService,
    temporal_context_service,
)
from backend.services.context_graph_service import (
    ContextGraphService,
    ContextGraphError,
    context_graph_service,
)
from backend.graph.models import (
    REL_POWERS,
    REL_DRIVES,
    REL_MONITORED_BY,
    REL_RELATED_TO,
    REL_SUPPORTED_BY,
    REL_RELATES_TO,
)

logger = logging.getLogger(__name__)

# Standard RRF smoothing constant
RRF_K = 60


class HybridRetrievalError(Exception):
    """Exception raised for errors during hybrid retrieval."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class HybridRetrievalService:
    """Orchestrates deterministic multi-channel evidence retrieval and context enrichment."""

    def __init__(
        self,
        vector_service: Optional[VectorIndexService] = None,
        keyword_service: Optional[KeywordEvidenceSearchService] = None,
        id_service: Optional[IdentifierRecognitionService] = None,
        temporal_service: Optional[TemporalContextService] = None,
        graph_service: Optional[ContextGraphService] = None,
    ):
        self._vector_service = vector_service
        self._keyword_service = keyword_service
        self._id_service = id_service or identifier_recognition_service
        self._temporal_service = temporal_service or temporal_context_service
        self._graph_service = graph_service

    @property
    def vector_service(self) -> VectorIndexService:
        if self._vector_service is not None:
            return self._vector_service
        return get_vector_index_service()

    @property
    def keyword_service(self) -> KeywordEvidenceSearchService:
        if self._keyword_service is not None:
            return self._keyword_service
        return keyword_evidence_search_service

    @property
    def graph_service(self) -> ContextGraphService:
        if self._graph_service is not None:
            return self._graph_service
        return context_graph_service

    def search_hybrid(
        self,
        incident_id: str,
        query: str,
        top_k: int = 8,
        asset_id: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute deterministic hybrid retrieval and assemble grounded context.

        Flow:
        1. Validate incident exists and query meets constraints
        2. Extract explicit industrial identifiers deterministically
        3. Retrieve candidates via exact/keyword lexical service
        4. Retrieve candidates via semantic vector service (Qdrant)
        5. Fuse rankings using Reciprocal Rank Fusion (RRF, k=60)
        6. Deduplicate evidence chunks while preserving multiple channels
        7. Expand bounded 1-2 hop equipment and evidence context in Neo4j
        8. Order chronological temporal events
        9. Assemble grounded context response
        """
        # 1. Validation
        if not incident_id or not incident_id.strip():
            raise HybridRetrievalError("A valid incident_id is required.", status_code=400)

        incident = incident_service.get_incident_by_id(incident_id)
        if not incident:
            raise HybridRetrievalError(f"Incident '{incident_id}' not found.", status_code=404)

        if not query or not query.strip():
            raise HybridRetrievalError("Search query must not be empty.", status_code=400)

        query_clean = query.strip()
        if len(query_clean) > 1000:
            raise HybridRetrievalError("Query exceeds maximum allowable length of 1000 characters.", status_code=400)

        # Enforce top_k constraints: default 8, capped between 1 and 20
        bounded_top_k = min(max(1, top_k), 20)
        candidate_pool_size = min(bounded_top_k * 2, 30)

        # 2. Extract identifiers
        recognized_identifiers = self._id_service.extract_identifiers(query_clean)

        # 3. Lexical / Keyword Retrieval Channel
        keyword_results: List[Dict[str, Any]] = []
        try:
            keyword_results = self.keyword_service.search(
                incident_id=incident_id,
                query=query_clean,
                top_k=candidate_pool_size,
                asset_id=asset_id,
                source_type=source_type,
                recognized_identifiers=recognized_identifiers,
            )
        except Exception as e:
            logger.warning("[RETRACE] Keyword search encounter: %s", str(e))

        # 4. Semantic Vector Retrieval Channel (Qdrant)
        semantic_results: List[Dict[str, Any]] = []
        try:
            sem_resp = self.vector_service.semantic_search(
                incident_id=incident_id,
                query=query_clean,
                top_k=candidate_pool_size,
                asset_id=asset_id,
                source_type=source_type,
            )
            semantic_results = sem_resp.get("results", [])
        except VectorServiceError as e:
            # If Qdrant is unavailable, do not invent results.
            # In production, if neither channel is available or error is fatal, report accurately.
            logger.warning("[RETRACE] Semantic retrieval unavailable: %s", e.message)
            if settings.ENVIRONMENT == "production" and not keyword_results:
                raise HybridRetrievalError(e.message, status_code=e.status_code)
        except Exception as e:
            logger.warning("[RETRACE] Unexpected semantic retrieval error: %s", type(e).__name__)
            if settings.ENVIRONMENT == "production" and not keyword_results:
                raise HybridRetrievalError(f"Vector search failed: {type(e).__name__}", status_code=500)

        # 5 & 6. Reciprocal Rank Fusion & Deduplication
        # Map: chunk_id -> fused accumulator dict
        fused_map: Dict[str, Dict[str, Any]] = {}

        # Process Semantic Channel
        for s_idx, s_item in enumerate(semantic_results, start=1):
            c_id = s_item["chunk_id"]
            if c_id not in fused_map:
                fused_map[c_id] = {
                    "chunk_id": c_id,
                    "evidence_id": s_item["evidence_id"],
                    "asset_id": s_item.get("asset_id"),
                    "filename": s_item["filename"],
                    "source_type": s_item["source_type"],
                    "text": s_item["text"],
                    "timestamp": s_item.get("timestamp"),
                    "provenance": s_item.get("provenance", {}),
                    "semantic_rank": s_idx,
                    "similarity_score": s_item.get("similarity_score"),
                    "keyword_rank": None,
                    "keyword_score": None,
                    "retrieval_channels": ["semantic"],
                    "rrf_score": 1.0 / (RRF_K + s_idx),
                }
            else:
                fused_map[c_id]["semantic_rank"] = s_idx
                fused_map[c_id]["similarity_score"] = s_item.get("similarity_score")
                if "semantic" not in fused_map[c_id]["retrieval_channels"]:
                    fused_map[c_id]["retrieval_channels"].append("semantic")
                fused_map[c_id]["rrf_score"] += 1.0 / (RRF_K + s_idx)

        # Process Keyword Channel
        for k_idx, k_item in enumerate(keyword_results, start=1):
            c_id = k_item["chunk_id"]
            if c_id not in fused_map:
                channels = ["keyword"]
                if k_item.get("has_identifier_match"):
                    channels.append("identifier")
                fused_map[c_id] = {
                    "chunk_id": c_id,
                    "evidence_id": k_item["evidence_id"],
                    "asset_id": k_item.get("asset_id"),
                    "filename": k_item["filename"],
                    "source_type": k_item["source_type"],
                    "text": k_item["text"],
                    "timestamp": k_item.get("timestamp"),
                    "provenance": k_item.get("provenance", {}),
                    "semantic_rank": None,
                    "similarity_score": None,
                    "keyword_rank": k_idx,
                    "keyword_score": k_item.get("keyword_score"),
                    "retrieval_channels": channels,
                    "rrf_score": 1.0 / (RRF_K + k_idx),
                }
            else:
                fused_map[c_id]["keyword_rank"] = k_idx
                fused_map[c_id]["keyword_score"] = k_item.get("keyword_score")
                if "keyword" not in fused_map[c_id]["retrieval_channels"]:
                    fused_map[c_id]["retrieval_channels"].append("keyword")
                if k_item.get("has_identifier_match") and "identifier" not in fused_map[c_id]["retrieval_channels"]:
                    fused_map[c_id]["retrieval_channels"].append("identifier")
                fused_map[c_id]["rrf_score"] += 1.0 / (RRF_K + k_idx)
                # If timestamp or provenance was missing from semantic result, backfill from keyword
                if not fused_map[c_id].get("timestamp") and k_item.get("timestamp"):
                    fused_map[c_id]["timestamp"] = k_item.get("timestamp")
                if not fused_map[c_id].get("provenance") and k_item.get("provenance"):
                    fused_map[c_id]["provenance"] = k_item.get("provenance")

        # Sort by fused rrf_score descending, with deterministic tie-breaking
        fused_list = list(fused_map.values())
        fused_list.sort(
            key=lambda item: (-item["rrf_score"], item["chunk_id"], item["evidence_id"])
        )

        # Slice top_k
        top_fused = fused_list[:bounded_top_k]

        # Format final HybridEvidenceResults
        final_evidence: List[Dict[str, Any]] = []
        retrieved_ev_ids: Set[str] = set()
        retrieved_asset_ids: Set[str] = set()

        for final_rank, item in enumerate(top_fused, start=1):
            retrieved_ev_ids.add(item["evidence_id"])
            if item.get("asset_id"):
                retrieved_asset_ids.add(item["asset_id"])

            final_evidence.append(
                {
                    "rank": final_rank,
                    "retrieval_score": round(item["rrf_score"], 6),
                    "retrieval_channels": item["retrieval_channels"],
                    "semantic_rank": item["semantic_rank"],
                    "similarity_score": item["similarity_score"],
                    "keyword_rank": item["keyword_rank"],
                    "keyword_score": item["keyword_score"],
                    "evidence_id": item["evidence_id"],
                    "chunk_id": item["chunk_id"],
                    "asset_id": item.get("asset_id"),
                    "filename": item["filename"],
                    "source_type": item["source_type"],
                    "text": item["text"],
                    "timestamp": item.get("timestamp"),
                    "provenance": item.get("provenance", {}),
                }
            )

        # 7. Neo4j Context Graph Expansion (1-2 hops, bounded)
        graph_context = self._expand_graph_context(
            incident_id=incident_id,
            retrieved_evidence_ids=retrieved_ev_ids,
            retrieved_asset_ids=retrieved_asset_ids,
            recognized_identifiers=recognized_identifiers,
        )

        # 8. Temporal Context Sequencing
        temporal_events = self._temporal_service.get_temporal_context(
            incident_id=incident_id,
            retrieved_evidence_ids=retrieved_ev_ids,
            retrieved_asset_ids=retrieved_asset_ids,
        )

        temporal_event_dicts = [
            t.model_dump() if hasattr(t, "model_dump") else t.dict() if hasattr(t, "dict") else dict(t)
            for t in temporal_events
        ]

        # 9. Return structured response payload
        return {
            "incident_id": incident_id,
            "query": query_clean,
            "recognized_identifiers": recognized_identifiers,
            "evidence": final_evidence,
            "graph_context": graph_context,
            "temporal_context": temporal_event_dicts,
        }

    def _expand_graph_context(
        self,
        incident_id: str,
        retrieved_evidence_ids: Set[str],
        retrieved_asset_ids: Set[str],
        recognized_identifiers: List[str],
    ) -> Dict[str, Any]:
        """Expand bounded 1-2 hop equipment topology and evidence relationships from Neo4j."""
        seed_assets = set(retrieved_asset_ids)
        for ident in recognized_identifiers:
            if self._id_service.is_asset_tag(ident):
                seed_assets.add(ident)

        # Default fallback topology if graph call fails
        topology_edges: List[Dict[str, Any]] = []
        assets_out: List[Dict[str, Any]] = []

        try:
            subgraph = self.graph_service.get_incident_graph(incident_id)
            nodes = subgraph.get("nodes", [])
            edges = subgraph.get("edges", [])

            nodes_by_id = {n["id"]: n for n in nodes if "id" in n}

            # 1. Expand asset seeds if evidence is connected to assets via edges
            for edge in edges:
                src = edge.get("source")
                tgt = edge.get("target")
                rel = edge.get("relationship", "")
                if rel in (REL_RELATED_TO, "related_to", "RELATED_TO"):
                    if src in retrieved_evidence_ids and tgt in nodes_by_id:
                        seed_assets.add(tgt)
                    elif tgt in retrieved_evidence_ids and src in nodes_by_id:
                        seed_assets.add(src)

            # If no asset seeds found, include the primary incident equipment
            if not seed_assets:
                seed_assets = {"VFD-204", "M-204", "P-204", "PLC-204"}

            # 2. Collect 1-2 hop physical topology relationships between equipment assets
            relevant_asset_ids = set(seed_assets)
            selected_edges: List[Dict[str, Any]] = []
            seen_edge_signatures: Set[str] = set()

            physical_rels = {
                REL_POWERS, "powers", "POWERS",
                REL_DRIVES, "drives", "DRIVES",
                REL_MONITORED_BY, "monitored by", "monitored_by", "MONITORED_BY",
            }

            for edge in edges:
                src = edge.get("source")
                tgt = edge.get("target")
                rel = edge.get("relationship", "")
                sig = f"{src}->{rel}->{tgt}"

                if rel in physical_rels:
                    if src in seed_assets or tgt in seed_assets or src in relevant_asset_ids or tgt in relevant_asset_ids:
                        if sig not in seen_edge_signatures:
                            seen_edge_signatures.add(sig)
                            selected_edges.append(edge)
                            relevant_asset_ids.add(src)
                            relevant_asset_ids.add(tgt)

            # Second hop for physical topology to ensure full drive cascade (VFD -> M -> P -> PLC)
            for edge in edges:
                src = edge.get("source")
                tgt = edge.get("target")
                rel = edge.get("relationship", "")
                sig = f"{src}->{rel}->{tgt}"
                if rel in physical_rels and sig not in seen_edge_signatures:
                    if src in relevant_asset_ids or tgt in relevant_asset_ids:
                        seen_edge_signatures.add(sig)
                        selected_edges.append(edge)
                        relevant_asset_ids.add(src)
                        relevant_asset_ids.add(tgt)

            # Format selected assets (capped at 8)
            for aid in sorted(list(relevant_asset_ids))[:8]:
                node_data = nodes_by_id.get(aid, {})
                meta = node_data.get("metadata", {})
                assets_out.append(
                    {
                        "id": aid,
                        "name": node_data.get("label") or meta.get("name") or aid,
                        "type": meta.get("type", "Industrial Equipment"),
                        "criticality": meta.get("criticality", "High"),
                        "status": meta.get("status", "Active"),
                    }
                )

            # Format relationships (capped at 12)
            for e in selected_edges[:12]:
                meta = e.get("metadata", {})
                topology_edges.append(
                    {
                        "source": e.get("source"),
                        "target": e.get("target"),
                        "relationship": e.get("relationship"),
                        "description": meta.get("description"),
                    }
                )

        except Exception as e:
            logger.warning("[RETRACE] Graph expansion fallback: %s", type(e).__name__)
            # Clean baseline equipment fallback
            incident_assets = incident_service.get_incident_assets(incident_id)
            for a in incident_assets:
                assets_out.append(
                    {
                        "id": a.id,
                        "name": a.name,
                        "type": a.type,
                        "criticality": a.criticality,
                        "status": a.status,
                    }
                )
            rel_list = incident_service.get_asset_relationships(incident_id)
            for r in rel_list:
                topology_edges.append(
                    {
                        "source": r.source_asset_id,
                        "target": r.target_asset_id,
                        "relationship": r.relation_type,
                        "description": r.description,
                    }
                )

        return {
            "assets": assets_out,
            "relationships": topology_edges,
        }


# Singleton and dependency injection hooks
_hybrid_retrieval_service_instance: Optional[HybridRetrievalService] = None


def get_hybrid_retrieval_service() -> HybridRetrievalService:
    """Retrieve singleton HybridRetrievalService instance."""
    global _hybrid_retrieval_service_instance
    if _hybrid_retrieval_service_instance is not None:
        return _hybrid_retrieval_service_instance

    _hybrid_retrieval_service_instance = HybridRetrievalService()
    return _hybrid_retrieval_service_instance


def set_hybrid_retrieval_service(service: Optional[HybridRetrievalService]) -> None:
    """Set or override singleton for testing."""
    global _hybrid_retrieval_service_instance
    _hybrid_retrieval_service_instance = service
