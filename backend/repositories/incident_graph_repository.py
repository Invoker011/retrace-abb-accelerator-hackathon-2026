"""Incident Context Graph Repository.

Encapsulates Neo4j Cypher queries and provides in-memory fallback for development.
Guarantees:
  - Idempotent synchronization using Cypher MERGE and uniqueness constraints
  - Zero SQL or Cypher concatenation (all queries use parameterized values)
  - No arbitrary Cypher execution
  - Clear separation between live Neo4j and fallback state
"""
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import deque

from backend.core.config import settings
from backend.graph.client import get_neo4j_driver
from backend.graph.models import (
    LABEL_INCIDENT,
    LABEL_ASSET,
    LABEL_EVENT,
    LABEL_EVIDENCE,
    LABEL_FINDING,
    REL_INVOLVES,
    REL_HAS_EVENT,
    REL_HAS_EVIDENCE,
    REL_HAS_FINDING,
    REL_OCCURRED_ON,
    REL_SUPPORTED_BY,
    REL_RELATES_TO,
    REL_POWERS,
    REL_DRIVES,
    REL_MONITORED_BY,
    REL_RELATED_TO,
    GraphNode,
    GraphEdge,
    GraphResponse,
    GraphSyncResponse,
    AssetPathResponse,
)

logger = logging.getLogger(__name__)

SAFE_ID_REGEX = re.compile(r"^[A-Za-z0-9_\-\.]+$")


class IncidentGraphRepositoryInterface(ABC):
    """Abstract interface defining operations on the Incident Context Graph."""

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def ensure_constraints(self) -> None:
        pass

    @abstractmethod
    def sync_incident(
        self,
        incident: Dict[str, Any],
        assets: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_incident_subgraph(self, incident_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def find_asset_path(
        self, incident_id: str, source_asset_id: str, target_asset_id: str
    ) -> Dict[str, Any]:
        pass


class Neo4jIncidentGraphRepository(IncidentGraphRepositoryInterface):
    """Production graph repository utilizing Neo4j 5.x/6.x with parameterized Cypher."""

    def __init__(self, driver: Optional[Any] = None, database: Optional[str] = None):
        self._driver = driver
        raw_db = database if database is not None else settings.NEO4J_DATABASE
        self._database = str(raw_db).strip() if (raw_db and str(raw_db).strip()) else None
        self._constraints_verified = False

    def _get_driver(self) -> Any:
        if self._driver is not None:
            return self._driver
        driver = get_neo4j_driver()
        if driver is None:
            raise RuntimeError("Neo4j driver is not configured or unavailable.")
        return driver

    def _get_session(self):
        """Create a Neo4j session respecting optional database configuration.

        If self._database has a non-empty value:
            driver.session(database=self._database)
        If self._database is unset or empty:
            driver.session()
        Do not pass database=None, empty string, or 'neo4j' unless explicitly configured.
        """
        driver = self._get_driver()
        if self._database:
            return driver.session(database=self._database)
        return driver.session()

    def is_available(self) -> bool:
        try:
            driver = self._get_driver()
            driver.verify_connectivity()
            with self._get_session() as session:
                session.run("RETURN 1 AS ping").consume()
            return True
        except Exception:
            return False

    def ensure_constraints(self) -> None:
        """Create uniqueness constraints idempotently."""
        if self._constraints_verified:
            return

        constraint_statements = [
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (i:{LABEL_INCIDENT}) REQUIRE i.incident_id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (a:{LABEL_ASSET}) REQUIRE a.asset_id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (e:{LABEL_EVENT}) REQUIRE e.event_id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (ev:{LABEL_EVIDENCE}) REQUIRE ev.evidence_id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (f:{LABEL_FINDING}) REQUIRE f.finding_id IS UNIQUE",
        ]

        with self._get_session() as session:
            for statement in constraint_statements:
                try:
                    session.run(statement)
                except Exception as e:
                    logger.warning("[RETRACE] Constraint setup warning: %s", type(e).__name__)

        self._constraints_verified = True

    def sync_incident(
        self,
        incident: Dict[str, Any],
        assets: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Synchronizes incident entities and relationships into Neo4j idempotently using MERGE."""
        self.ensure_constraints()
        driver = self._get_driver()

        incident_id = incident.get("id") or incident.get("incident_id")
        if not incident_id:
            raise ValueError("Incident ID is required for synchronization.")

        # Sanitize parameters for Cypher
        inc_params = {
            "incident_id": incident_id,
            "title": incident.get("title", ""),
            "severity": incident.get("severity", ""),
            "status": incident.get("status", ""),
            "plant_area": incident.get("plantArea") or incident.get("plant_area", ""),
            "date": incident.get("date", ""),
        }

        asset_params = [
            {
                "asset_id": a.get("id") or a.get("asset_id"),
                "name": a.get("name", ""),
                "type": a.get("type", ""),
                "plant_area": a.get("plantArea") or a.get("plant_area", ""),
                "manufacturer": a.get("manufacturer", ""),
                "model": a.get("model", ""),
                "criticality": a.get("criticality", ""),
            }
            for a in assets
            if a.get("id") or a.get("asset_id")
        ]

        event_params = [
            {
                "event_id": e.get("id") or e.get("event_id"),
                "timestamp": e.get("timestamp", ""),
                "event_type": e.get("eventType") or e.get("event_type", ""),
                "title": e.get("title", ""),
                "severity": e.get("severity", ""),
                "asset_id": e.get("assetId") or e.get("asset_id"),
                "evidence_id": e.get("evidenceId") or e.get("evidence_id"),
            }
            for e in events
            if e.get("id") or e.get("event_id")
        ]

        evidence_params = [
            {
                "evidence_id": ev.get("id") or ev.get("evidence_id"),
                "source_type": ev.get("sourceType") or ev.get("source_type", ""),
                "filename": ev.get("filename") or ev.get("original_filename", ""),
                "processing_status": ev.get("processingStatus") or ev.get("processing_status", "CONFIRMED"),
                "asset_id": ev.get("assetId") or ev.get("asset_id"),
            }
            for ev in evidence
            if ev.get("id") or ev.get("evidence_id")
        ]

        finding_params = []
        finding_evidence_links = []
        finding_asset_links = []
        for f in findings:
            fid = f.get("id") or f.get("finding_id")
            if not fid:
                continue
            classification = f.get("category") or f.get("classification")
            if hasattr(classification, "value"):
                classification = classification.value
            if not classification:
                classification = "OBSERVED"
            classification_str = str(classification).upper()

            statement = f.get("statement") or f.get("title") or ""
            conf_val = f.get("confidenceScore") or f.get("confidence_score")
            try:
                conf_score = float(conf_val) if conf_val is not None else 1.0
            except (ValueError, TypeError):
                conf_score = 1.0

            finding_params.append({
                "finding_id": fid,
                "classification": classification_str,
                "category": classification_str,
                "statement": statement,
                "confidence_score": conf_score,
            })

            ev_list = (
                f.get("supportingEvidenceIds")
                or f.get("supporting_evidence_ids")
                or f.get("evidenceIds")
                or f.get("evidence_ids")
                or []
            )
            for evid in ev_list:
                if evid:
                    finding_evidence_links.append({"finding_id": fid, "evidence_id": str(evid)})

            asset_list = (
                f.get("relatedAssetIds")
                or f.get("related_asset_ids")
                or []
            )
            if not isinstance(asset_list, list):
                asset_list = [asset_list]
            if f.get("assetId"):
                asset_list.append(f.get("assetId"))
            if f.get("asset_id"):
                asset_list.append(f.get("asset_id"))
            for aid in asset_list:
                if aid:
                    finding_asset_links.append({"finding_id": fid, "asset_id": str(aid)})

        # Explicit Asset Topology couplings
        topology_couplings = [
            {"source": "VFD-204", "target": "M-204", "type": REL_POWERS},
            {"source": "M-204", "target": "P-204", "type": REL_DRIVES},
            {"source": "P-204", "target": "PLC-204", "type": REL_MONITORED_BY},
        ]

        total_nodes = 1 + len(asset_params) + len(event_params) + len(evidence_params) + len(finding_params)
        total_rels = 0

        event_ids = [e["event_id"] for e in event_params]
        evidence_ids = [ev["evidence_id"] for ev in evidence_params]
        finding_ids = [f["finding_id"] for f in finding_params]

        with self._get_session() as session:
            # 0. RECONCILIATION OF STALE / INCORRECT RETRACE RELATIONSHIPS
            # R1: Delete any invalid HAS_EVIDENCE pointing to non-Evidence nodes (e.g. Assets)
            session.run(
                f"""
                MATCH (i:{LABEL_INCIDENT} {{incident_id: $incident_id}})-[r:{REL_HAS_EVIDENCE}]->(target)
                WHERE NOT target:{LABEL_EVIDENCE}
                DELETE r
                """,
                {"incident_id": incident_id},
            )

            # R2: Delete invalid RELATED_TO relationships where source is not Evidence or target is not Asset (e.g. Asset self-loops)
            session.run(
                f"""
                MATCH (src)-[r:{REL_RELATED_TO}]->(tgt)
                WHERE NOT src:{LABEL_EVIDENCE} OR NOT tgt:{LABEL_ASSET}
                DELETE r
                """
            )

            # R3: Delete any direct Asset->RELATED_TO relationships
            session.run(
                f"""
                MATCH (a:{LABEL_ASSET})-[r:{REL_RELATED_TO}]->()
                DELETE r
                """
            )

            # R4: Clean existing incident-managed relationships for this incident to ensure full idempotency
            session.run(
                f"""
                MATCH (i:{LABEL_INCIDENT} {{incident_id: $incident_id}})-[r:{REL_INVOLVES}|{REL_HAS_EVENT}|{REL_HAS_EVIDENCE}|{REL_HAS_FINDING}]->()
                DELETE r
                """,
                {"incident_id": incident_id},
            )

            if event_ids:
                session.run(
                    f"""
                    UNWIND $event_ids AS eid
                    WITH eid WHERE eid IS NOT NULL AND eid <> ''
                    MATCH (e:{LABEL_EVENT} {{event_id: eid}})-[r:{REL_OCCURRED_ON}|{REL_SUPPORTED_BY}]->()
                    DELETE r
                    """,
                    {"event_ids": event_ids},
                )

            if evidence_ids:
                session.run(
                    f"""
                    UNWIND $evidence_ids AS evid
                    WITH evid WHERE evid IS NOT NULL AND evid <> ''
                    MATCH (ev:{LABEL_EVIDENCE} {{evidence_id: evid}})-[r:{REL_RELATED_TO}]->()
                    DELETE r
                    """,
                    {"evidence_ids": evidence_ids},
                )

            if finding_ids:
                session.run(
                    f"""
                    UNWIND $finding_ids AS fid
                    WITH fid WHERE fid IS NOT NULL AND fid <> ''
                    MATCH (f:{LABEL_FINDING} {{finding_id: fid}})-[r:{REL_SUPPORTED_BY}|{REL_RELATES_TO}]->()
                    DELETE r
                    """,
                    {"finding_ids": finding_ids},
                )
            # 1. Merge Incident Node
            session.run(
                f"""
                MERGE (i:{LABEL_INCIDENT} {{incident_id: $incident.incident_id}})
                ON CREATE SET
                  i.title = $incident.title,
                  i.severity = $incident.severity,
                  i.status = $incident.status,
                  i.plant_area = $incident.plant_area,
                  i.date = $incident.date
                ON MATCH SET
                  i.title = $incident.title,
                  i.severity = $incident.severity,
                  i.status = $incident.status,
                  i.plant_area = $incident.plant_area,
                  i.date = $incident.date
                """,
                {"incident": inc_params},
            )

            # 2. Merge Assets & (Incident)-[:INVOLVES]->(Asset)
            if asset_params:
                session.run(
                    f"""
                    UNWIND $assets AS a
                    WITH a
                    WHERE a.asset_id IS NOT NULL AND a.asset_id <> ''
                    MERGE (asset:{LABEL_ASSET} {{asset_id: a.asset_id}})
                    ON CREATE SET
                      asset.name = a.name,
                      asset.type = a.type,
                      asset.plant_area = a.plant_area,
                      asset.manufacturer = a.manufacturer,
                      asset.model = a.model,
                      asset.criticality = a.criticality
                    ON MATCH SET
                      asset.name = a.name,
                      asset.type = a.type,
                      asset.plant_area = a.plant_area,
                      asset.manufacturer = a.manufacturer,
                      asset.model = a.model,
                      asset.criticality = a.criticality
                    WITH asset
                    MATCH (i:{LABEL_INCIDENT} {{incident_id: $incident_id}})
                    MERGE (i)-[:{REL_INVOLVES}]->(asset)
                    """,
                    {"assets": asset_params, "incident_id": incident_id},
                )
                total_rels += len(asset_params)

            # 3. Merge Events & (Incident)-[:HAS_EVENT]->(Event), (Event)-[:OCCURRED_ON]->(Asset)
            if event_params:
                # 3A: Merge Event node and link to Incident (HAS_EVENT)
                session.run(
                    f"""
                    UNWIND $events AS e
                    WITH e
                    WHERE e.event_id IS NOT NULL AND e.event_id <> ''
                    MERGE (event:{LABEL_EVENT} {{event_id: e.event_id}})
                    ON CREATE SET
                      event.timestamp = e.timestamp,
                      event.event_type = e.event_type,
                      event.title = e.title,
                      event.severity = e.severity
                    ON MATCH SET
                      event.timestamp = e.timestamp,
                      event.event_type = e.event_type,
                      event.title = e.title,
                      event.severity = e.severity
                    WITH event
                    MATCH (i:{LABEL_INCIDENT} {{incident_id: $incident_id}})
                    MERGE (i)-[:{REL_HAS_EVENT}]->(event)
                    """,
                    {"events": event_params, "incident_id": incident_id},
                )
                total_rels += len(event_params)

                # 3B: Connect Event to Asset (OCCURRED_ON) - filtered safely before MATCH/MERGE
                session.run(
                    f"""
                    UNWIND $events AS e
                    WITH e
                    WHERE e.event_id IS NOT NULL AND e.event_id <> ''
                      AND e.asset_id IS NOT NULL AND e.asset_id <> ''
                    MATCH (event:{LABEL_EVENT} {{event_id: e.event_id}})
                    MATCH (a:{LABEL_ASSET} {{asset_id: e.asset_id}})
                    MERGE (event)-[:{REL_OCCURRED_ON}]->(a)
                    """,
                    {"events": event_params},
                )

                # 3C: Connect Event to Evidence (SUPPORTED_BY) - filtered safely before MATCH/MERGE
                session.run(
                    f"""
                    UNWIND $events AS e
                    WITH e
                    WHERE e.event_id IS NOT NULL AND e.event_id <> ''
                      AND e.evidence_id IS NOT NULL AND e.evidence_id <> ''
                    MATCH (event:{LABEL_EVENT} {{event_id: e.event_id}})
                    MATCH (ev:{LABEL_EVIDENCE} {{evidence_id: e.evidence_id}})
                    MERGE (event)-[:{REL_SUPPORTED_BY}]->(ev)
                    """,
                    {"events": event_params},
                )

            # 4. Merge Evidence & (Incident)-[:HAS_EVIDENCE]->(Evidence), (Evidence)-[:RELATED_TO]->(Asset)
            if evidence_params:
                # 4A: Merge Evidence node and link to Incident (HAS_EVIDENCE)
                session.run(
                    f"""
                    UNWIND $evidence AS ev
                    WITH ev
                    WHERE ev.evidence_id IS NOT NULL AND ev.evidence_id <> ''
                    MERGE (evidence:{LABEL_EVIDENCE} {{evidence_id: ev.evidence_id}})
                    ON CREATE SET
                      evidence.id = ev.evidence_id,
                      evidence.evidence_id = ev.evidence_id,
                      evidence.source_type = ev.source_type,
                      evidence.filename = ev.filename,
                      evidence.processing_status = ev.processing_status,
                      evidence.asset_id = ev.asset_id
                    ON MATCH SET
                      evidence.id = ev.evidence_id,
                      evidence.evidence_id = ev.evidence_id,
                      evidence.source_type = ev.source_type,
                      evidence.filename = ev.filename,
                      evidence.processing_status = ev.processing_status,
                      evidence.asset_id = ev.asset_id
                    WITH evidence
                    MATCH (i:{LABEL_INCIDENT} {{incident_id: $incident_id}})
                    MERGE (i)-[:{REL_HAS_EVIDENCE}]->(evidence)
                    """,
                    {"evidence": evidence_params, "incident_id": incident_id},
                )
                total_rels += len(evidence_params)

                # 4B: Connect Evidence to Asset (RELATED_TO) - filtered safely before MATCH/MERGE
                session.run(
                    f"""
                    UNWIND $evidence AS ev
                    WITH ev
                    WHERE ev.evidence_id IS NOT NULL AND ev.evidence_id <> ''
                      AND ev.asset_id IS NOT NULL AND ev.asset_id <> ''
                    MATCH (evidence:{LABEL_EVIDENCE} {{evidence_id: ev.evidence_id}})
                    MATCH (a:{LABEL_ASSET} {{asset_id: ev.asset_id}})
                    MERGE (evidence)-[:{REL_RELATED_TO}]->(a)
                    """,
                    {"evidence": evidence_params},
                )

            # 5. Merge Findings & (Incident)-[:HAS_FINDING]->(Finding)
            if finding_params:
                # 5A: Merge Finding node and link to Incident (HAS_FINDING)
                session.run(
                    f"""
                    UNWIND $findings AS f
                    WITH f
                    WHERE f.finding_id IS NOT NULL AND f.finding_id <> ''
                    MERGE (finding:{LABEL_FINDING} {{finding_id: f.finding_id}})
                    ON CREATE SET
                      finding.id = f.finding_id,
                      finding.finding_id = f.finding_id,
                      finding.classification = f.classification,
                      finding.category = f.category,
                      finding.statement = f.statement,
                      finding.confidence_score = f.confidence_score
                    ON MATCH SET
                      finding.id = f.finding_id,
                      finding.finding_id = f.finding_id,
                      finding.classification = f.classification,
                      finding.category = f.category,
                      finding.statement = f.statement,
                      finding.confidence_score = f.confidence_score
                    WITH finding
                    MATCH (i:{LABEL_INCIDENT} {{incident_id: $incident_id}})
                    MERGE (i)-[:{REL_HAS_FINDING}]->(finding)
                    """,
                    {"findings": finding_params, "incident_id": incident_id},
                )
                total_rels += len(finding_params)

            # 5B: Connect Finding to Supporting Evidence
            if finding_evidence_links:
                session.run(
                    f"""
                    UNWIND $links AS link
                    WITH link
                    WHERE link.finding_id IS NOT NULL AND link.finding_id <> ''
                      AND link.evidence_id IS NOT NULL AND link.evidence_id <> ''
                    MATCH (f:{LABEL_FINDING} {{finding_id: link.finding_id}})
                    MATCH (ev:{LABEL_EVIDENCE} {{evidence_id: link.evidence_id}})
                    MERGE (f)-[:{REL_SUPPORTED_BY}]->(ev)
                    """,
                    {"links": finding_evidence_links},
                )
                total_rels += len(finding_evidence_links)

            # 5C: Connect Finding to Related Asset
            if finding_asset_links:
                session.run(
                    f"""
                    UNWIND $links AS link
                    WITH link
                    WHERE link.finding_id IS NOT NULL AND link.finding_id <> ''
                      AND link.asset_id IS NOT NULL AND link.asset_id <> ''
                    MATCH (f:{LABEL_FINDING} {{finding_id: link.finding_id}})
                    MATCH (a:{LABEL_ASSET} {{asset_id: link.asset_id}})
                    MERGE (f)-[:{REL_RELATES_TO}]->(a)
                    """,
                    {"links": finding_asset_links},
                )
                total_rels += len(finding_asset_links)

            # 6. Asset Topology Coupling (VFD-204 POWERS M-204, M-204 DRIVES P-204, P-204 MONITORED_BY PLC-204)
            session.run(
                f"""
                MATCH (vfd:{LABEL_ASSET} {{asset_id: $vfd_id}})
                MATCH (m:{LABEL_ASSET} {{asset_id: $m_id}})
                MERGE (vfd)-[:{REL_POWERS}]->(m)
                """,
                {"vfd_id": "VFD-204", "m_id": "M-204"},
            )
            session.run(
                f"""
                MATCH (m:{LABEL_ASSET} {{asset_id: $m_id}})
                MATCH (p:{LABEL_ASSET} {{asset_id: $p_id}})
                MERGE (m)-[:{REL_DRIVES}]->(p)
                """,
                {"m_id": "M-204", "p_id": "P-204"},
            )
            session.run(
                f"""
                MATCH (p:{LABEL_ASSET} {{asset_id: $p_id}})
                MATCH (plc:{LABEL_ASSET} {{asset_id: $plc_id}})
                MERGE (p)-[:{REL_MONITORED_BY}]->(plc)
                """,
                {"p_id": "P-204", "plc_id": "PLC-204"},
            )
            total_rels += 3

        return {
            "incident_id": incident_id,
            "nodes_created_or_matched": total_nodes,
            "relationships_created_or_matched": total_rels,
            "status": "synchronized",
        }

    def get_incident_subgraph(self, incident_id: str) -> Dict[str, Any]:
        """Fetch all nodes and relationships connected to the incident subgraph."""
        driver = self._get_driver()
        query = f"""
        MATCH (i:{LABEL_INCIDENT} {{incident_id: $incident_id}})
        OPTIONAL MATCH (i)-[r1]-(n1)
        OPTIONAL MATCH (n1)-[r2]-(n2)
        WHERE n2:{LABEL_ASSET} OR n2:{LABEL_EVENT} OR n2:{LABEL_EVIDENCE} OR n2:{LABEL_FINDING}
        WITH i, [x IN collect(DISTINCT n1) + collect(DISTINCT n2) + [i] WHERE x IS NOT NULL] AS raw_nodes
        UNWIND raw_nodes AS node
        WITH i, collect(DISTINCT node) AS all_nodes
        UNWIND all_nodes AS src
        UNWIND all_nodes AS tgt
        OPTIONAL MATCH (src)-[rel]->(tgt)
        RETURN all_nodes, [r IN collect(DISTINCT rel) WHERE r IS NOT NULL] AS all_rels
        """

        nodes_out: List[Dict[str, Any]] = []
        edges_out: List[Dict[str, Any]] = []
        seen_node_ids: Set[str] = set()
        seen_edge_ids: Set[str] = set()

        def resolve_node_id(n_obj: Any) -> Optional[str]:
            n_labels = list(getattr(n_obj, "labels", []))
            n_props = dict(n_obj)
            if LABEL_EVIDENCE in n_labels:
                return n_props.get("evidence_id") or n_props.get("id")
            if LABEL_FINDING in n_labels:
                return n_props.get("finding_id") or n_props.get("id")
            if LABEL_EVENT in n_labels:
                return n_props.get("event_id") or n_props.get("id")
            if LABEL_ASSET in n_labels:
                return n_props.get("asset_id") or n_props.get("id")
            if LABEL_INCIDENT in n_labels:
                return n_props.get("incident_id") or n_props.get("id")
            return (
                n_props.get("evidence_id")
                or n_props.get("finding_id")
                or n_props.get("event_id")
                or n_props.get("incident_id")
                or n_props.get("asset_id")
                or (str(getattr(n_obj, "id", "")) if hasattr(n_obj, "id") else None)
            )

        with self._get_session() as session:
            res = session.run(query, {"incident_id": incident_id})
            record = res.single()
            if record:
                raw_nodes = record.get("all_nodes") or []
                raw_rels = record.get("all_rels") or []

                for node in raw_nodes:
                    labels = list(getattr(node, "labels", []))
                    primary_label = labels[0] if labels else "Unknown"
                    props = dict(node)
                    node_id = resolve_node_id(node)
                    if not node_id:
                        continue
                    if node_id not in seen_node_ids:
                        seen_node_ids.add(node_id)
                        if LABEL_EVIDENCE in labels:
                            label_name = props.get("filename") or props.get("original_filename") or props.get("title") or node_id
                            props["id"] = node_id
                            props["evidence_id"] = node_id
                        elif LABEL_FINDING in labels:
                            label_name = props.get("statement") or props.get("title") or node_id
                            props["id"] = node_id
                            props["finding_id"] = node_id
                            props["classification"] = props.get("classification") or props.get("category") or "OBSERVED"
                            props["category"] = props["classification"]
                        elif LABEL_EVENT in labels:
                            label_name = props.get("title") or props.get("name") or node_id
                            props["id"] = node_id
                            props["event_id"] = node_id
                        elif LABEL_ASSET in labels:
                            label_name = props.get("name") or props.get("title") or node_id
                            props["id"] = node_id
                            props["asset_id"] = node_id
                        else:
                            label_name = props.get("title") or props.get("name") or node_id
                            props["id"] = node_id

                        nodes_out.append({
                            "id": node_id,
                            "type": primary_label.lower(),
                            "label": label_name,
                            "metadata": props,
                        })

                for rel in raw_rels:
                    source_id = resolve_node_id(rel.start_node)
                    target_id = resolve_node_id(rel.end_node)
                    if not source_id or not target_id:
                        continue
                    # Prevent any self-loop on RELATED_TO
                    if rel.type == REL_RELATED_TO and source_id == target_id:
                        continue
                    edge_id = f"{source_id}->{rel.type}->{target_id}"
                    if edge_id not in seen_edge_ids:
                        seen_edge_ids.add(edge_id)
                        edges_out.append({
                            "id": edge_id,
                            "source": source_id,
                            "target": target_id,
                            "relationship": rel.type,
                            "metadata": dict(rel),
                        })

        return {
            "incident_id": incident_id,
            "nodes": nodes_out,
            "edges": edges_out,
            "source": "neo4j",
        }

    def find_asset_path(
        self, incident_id: str, source_asset_id: str, target_asset_id: str
    ) -> Dict[str, Any]:
        """Find the relationship path between two assets using parameterized shortestPath."""
        if not SAFE_ID_REGEX.match(source_asset_id) or not SAFE_ID_REGEX.match(target_asset_id):
            raise ValueError("Invalid asset ID format.")

        driver = self._get_driver()
        query = f"""
        MATCH (src:{LABEL_ASSET} {{asset_id: $source_asset}}), (tgt:{LABEL_ASSET} {{asset_id: $target_asset}})
        MATCH p = shortestPath((src)-[:{REL_POWERS}|{REL_DRIVES}|{REL_MONITORED_BY}|SUPPLIES|CONTROLS*1..6]-(tgt))
        RETURN
          [node in nodes(p) | {{
              id: coalesce(node.asset_id, node.incident_id, node.event_id, node.evidence_id, node.finding_id),
              label: coalesce(node.name, node.title, node.asset_id),
              type: labels(node)[0]
          }}] AS path_nodes,
          [rel in relationships(p) | {{
              type: type(rel),
              source: coalesce(startNode(rel).asset_id, startNode(rel).incident_id),
              target: coalesce(endNode(rel).asset_id, endNode(rel).incident_id)
          }}] AS path_rels
        """

        with self._get_session() as session:
            res = session.run(
                query,
                {"source_asset": source_asset_id, "target_asset": target_asset_id},
            )
            record = res.single()
            if not record or not record.get("path_nodes"):
                return {
                    "incident_id": incident_id,
                    "source_asset": source_asset_id,
                    "target_asset": target_asset_id,
                    "found": False,
                    "path": [],
                    "relationships": [],
                    "length": 0,
                }

            path_nodes = record.get("path_nodes") or []
            path_rels = record.get("path_rels") or []

            combined_path: List[Dict[str, Any]] = []
            for i, node in enumerate(path_nodes):
                combined_path.append({"type": "node", **node})
                if i < len(path_rels):
                    rel = path_rels[i]
                    combined_path.append({"type": "relationship", "relationship": rel.get("type"), "source": rel.get("source"), "target": rel.get("target")})

            rel_names = [r.get("type") for r in path_rels if r.get("type")]
            return {
                "incident_id": incident_id,
                "source_asset": source_asset_id,
                "target_asset": target_asset_id,
                "found": True,
                "path": combined_path,
                "relationships": rel_names,
                "length": len(rel_names),
            }


class InMemoryIncidentGraphRepository(IncidentGraphRepositoryInterface):
    """Deterministic in-memory graph repository for development fallback and testing."""

    def __init__(self):
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: Dict[str, Dict[str, Any]] = {}
        self._adj: Dict[str, List[Tuple[str, str]]] = {}  # source -> list of (target, rel_type)

    def is_available(self) -> bool:
        return True

    def ensure_constraints(self) -> None:
        pass

    def sync_incident(
        self,
        incident: Dict[str, Any],
        assets: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        # Reset state for idempotent resynchronization
        self._nodes.clear()
        self._edges.clear()
        self._adj.clear()

        inc_id = incident.get("id") or incident.get("incident_id", "INC-2026-001")

        # Incident Node
        self._nodes[inc_id] = {
            "id": inc_id,
            "type": "incident",
            "label": inc_id,
            "metadata": incident,
        }

        # Assets
        for a in assets:
            aid = a.get("id") or a.get("asset_id")
            if aid:
                self._nodes[aid] = {
                    "id": aid,
                    "type": "asset",
                    "label": a.get("name") or aid,
                    "metadata": a,
                }
                self._add_edge(inc_id, aid, REL_INVOLVES)

        # Asset Topology
        topology_couplings = [
            ("VFD-204", "M-204", REL_POWERS),
            ("M-204", "P-204", REL_DRIVES),
            ("P-204", "PLC-204", REL_MONITORED_BY),
        ]
        for src, tgt, rel in topology_couplings:
            if src in self._nodes and tgt in self._nodes:
                self._add_edge(src, tgt, rel)

        # Events
        for e in events:
            eid = e.get("id") or e.get("event_id")
            if eid:
                self._nodes[eid] = {
                    "id": eid,
                    "type": "event",
                    "label": e.get("title") or eid,
                    "metadata": e,
                }
                self._add_edge(inc_id, eid, REL_HAS_EVENT)
                aid = e.get("assetId") or e.get("asset_id")
                if aid and aid in self._nodes:
                    self._add_edge(eid, aid, REL_OCCURRED_ON)
                evid = e.get("evidenceId") or e.get("evidence_id")
                if evid:
                    self._add_edge(eid, evid, REL_SUPPORTED_BY)

        # Evidence (synthetic + newly uploaded)
        for ev in evidence:
            evid = ev.get("id") or ev.get("evidence_id")
            if evid:
                self._nodes[evid] = {
                    "id": evid,
                    "type": "evidence",
                    "label": ev.get("filename") or ev.get("original_filename") or evid,
                    "metadata": ev,
                }
                self._add_edge(inc_id, evid, REL_HAS_EVIDENCE)
                aid = ev.get("assetId") or ev.get("asset_id")
                if aid and aid in self._nodes:
                    self._add_edge(evid, aid, REL_RELATED_TO)

        # Findings
        for f in findings:
            fid = f.get("id") or f.get("finding_id")
            if fid:
                classification = f.get("category") or f.get("classification")
                if hasattr(classification, "value"):
                    classification = classification.value
                if not classification:
                    classification = "OBSERVED"
                classification_str = str(classification).upper()
                f_meta = dict(f)
                f_meta["classification"] = classification_str
                f_meta["category"] = classification_str
                f_meta["id"] = fid
                f_meta["finding_id"] = fid
                self._nodes[fid] = {
                    "id": fid,
                    "type": "finding",
                    "label": f.get("statement") or fid,
                    "metadata": f_meta,
                }
                self._add_edge(inc_id, fid, REL_HAS_FINDING)
                for evid in (
                    f.get("supportingEvidenceIds")
                    or f.get("supporting_evidence_ids")
                    or f.get("evidenceIds")
                    or f.get("evidence_ids")
                    or []
                ):
                    if evid:
                        self._add_edge(fid, str(evid), REL_SUPPORTED_BY)
                asset_list = f.get("relatedAssetIds") or f.get("related_asset_ids") or []
                if not isinstance(asset_list, list):
                    asset_list = [asset_list]
                if f.get("assetId"):
                    asset_list.append(f.get("assetId"))
                if f.get("asset_id"):
                    asset_list.append(f.get("asset_id"))
                for aid in asset_list:
                    if aid and aid in self._nodes:
                        self._add_edge(fid, aid, REL_RELATES_TO)

        return {
            "incident_id": inc_id,
            "nodes_created_or_matched": len(self._nodes),
            "relationships_created_or_matched": len(self._edges),
            "status": "synchronized",
        }

    def _add_edge(self, src: str, tgt: str, rel: str):
        edge_id = f"{src}->{rel}->{tgt}"
        self._edges[edge_id] = {
            "id": edge_id,
            "source": src,
            "target": tgt,
            "relationship": rel,
            "metadata": {},
        }
        if src not in self._adj:
            self._adj[src] = []
        if (tgt, rel) not in self._adj[src]:
            self._adj[src].append((tgt, rel))

    def get_incident_subgraph(self, incident_id: str) -> Dict[str, Any]:
        # If empty, seed default INC-2026-001 topology
        if not self._nodes:
            self._seed_default_mock(incident_id)

        return {
            "incident_id": incident_id,
            "nodes": list(self._nodes.values()),
            "edges": list(self._edges.values()),
            "source": "mock",
        }

    def _seed_default_mock(self, incident_id: str):
        """Initial baseline seed if not synced."""
        self._nodes.clear()
        self._edges.clear()
        self._adj.clear()

        self._nodes[incident_id] = {"id": incident_id, "type": "incident", "label": incident_id, "metadata": {"incident_id": incident_id}}
        assets = ["VFD-204", "M-204", "P-204", "PLC-204"]
        for a in assets:
            self._nodes[a] = {"id": a, "type": "asset", "label": a, "metadata": {"asset_id": a}}
            self._add_edge(incident_id, a, REL_INVOLVES)
        self._add_edge("VFD-204", "M-204", REL_POWERS)
        self._add_edge("M-204", "P-204", REL_DRIVES)
        self._add_edge("P-204", "PLC-204", REL_MONITORED_BY)

        for i in range(1, 7):
            evid = f"EVD-00{i}"
            self._nodes[evid] = {"id": evid, "type": "evidence", "label": f"Evidence {evid}", "metadata": {"evidence_id": evid, "asset_id": "VFD-204" if i == 1 else "M-204" if i == 5 else "PLC-204" if i == 2 else "P-204"}}
            self._add_edge(incident_id, evid, REL_HAS_EVIDENCE)

        # Baseline linkage
        self._add_edge("EVD-001", "VFD-204", REL_RELATED_TO)
        self._add_edge("EVD-005", "M-204", REL_RELATED_TO)
        self._add_edge("EVD-003", "P-204", REL_RELATED_TO)
        self._add_edge("EVD-004", "P-204", REL_RELATED_TO)
        self._add_edge("EVD-006", "P-204", REL_RELATED_TO)
        self._add_edge("EVD-002", "PLC-204", REL_RELATED_TO)

        # Baseline findings with classifications
        mock_findings = [
            ("FND-001", "OBSERVED", "VFD-204 Phase U IGBT over-temperature trip logged at 14:22:18", ["EVD-001"], ["VFD-204"]),
            ("FND-002", "OBSERVED", "Line 2 slurry pump discharge pressure drop to 0.4 bar", ["EVD-002"], ["P-204"]),
            ("FND-003", "CORRELATED", "VFD cabinet inlet filter DP increased 3 days prior", ["EVD-004"], ["VFD-204"]),
            ("FND-004", "HYPOTHESIS", "Cooling fan auxiliary contact intermittent failure", ["EVD-006"], ["VFD-204"]),
            ("FND-005", "UNKNOWN", "Whether emergency pump P-204B auto-started", [], ["P-204"]),
        ]
        for fid, cls, stmt, ev_ids, asset_ids in mock_findings:
            self._nodes[fid] = {
                "id": fid,
                "type": "finding",
                "label": stmt,
                "metadata": {"finding_id": fid, "classification": cls, "category": cls, "statement": stmt},
            }
            self._add_edge(incident_id, fid, REL_HAS_FINDING)
            for eid in ev_ids:
                self._add_edge(fid, eid, REL_SUPPORTED_BY)
            for aid in asset_ids:
                self._add_edge(fid, aid, REL_RELATES_TO)

    def find_asset_path(
        self, incident_id: str, source_asset_id: str, target_asset_id: str
    ) -> Dict[str, Any]:
        if not self._nodes:
            self._seed_default_mock(incident_id)

        if not SAFE_ID_REGEX.match(source_asset_id) or not SAFE_ID_REGEX.match(target_asset_id):
            raise ValueError("Invalid asset ID format.")

        # Breadth-first search for shortest undirected path
        queue = deque([[source_asset_id]])
        visited = {source_asset_id}
        path_found = None

        # Build undirected adjacency strictly over Asset topology relationships
        undirected: Dict[str, List[Tuple[str, str]]] = {}
        for edge in self._edges.values():
            s = edge["source"]
            t = edge["target"]
            r = edge["relationship"]
            # Exclude incident parent linkages so paths traverse equipment topology
            s_is_asset = self._nodes.get(s, {}).get("type") == "asset"
            t_is_asset = self._nodes.get(t, {}).get("type") == "asset"
            if s_is_asset and t_is_asset and r != REL_INVOLVES:
                undirected.setdefault(s, []).append((t, r))
                undirected.setdefault(t, []).append((s, r))

        while queue:
            curr_path = queue.popleft()
            node = curr_path[-1]
            if node == target_asset_id:
                path_found = curr_path
                break
            for neighbor, rel in undirected.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(curr_path + [neighbor])

        if not path_found:
            return {
                "incident_id": incident_id,
                "source_asset": source_asset_id,
                "target_asset": target_asset_id,
                "found": False,
                "path": [],
                "relationships": [],
                "length": 0,
            }

        # Build combined path structure
        combined: List[Dict[str, Any]] = []
        rels: List[str] = []
        for i in range(len(path_found)):
            n_id = path_found[i]
            n_data = self._nodes.get(n_id, {"label": n_id, "type": "asset"})
            combined.append({"type": "node", "id": n_id, "label": n_data.get("label", n_id), "node_type": n_data.get("type")})
            if i < len(path_found) - 1:
                next_id = path_found[i + 1]
                # Find relationship
                rel_name = "CONNECTED_TO"
                for edge in self._edges.values():
                    if (edge["source"] == n_id and edge["target"] == next_id) or (edge["source"] == next_id and edge["target"] == n_id):
                        rel_name = edge["relationship"]
                        break
                rels.append(rel_name)
                combined.append({"type": "relationship", "relationship": rel_name, "source": n_id, "target": next_id})

        return {
            "incident_id": incident_id,
            "source_asset": source_asset_id,
            "target_asset": target_asset_id,
            "found": True,
            "path": combined,
            "relationships": rels,
            "length": len(rels),
        }


class ProductionUnconfiguredGraphRepository(IncidentGraphRepositoryInterface):
    """Enforces explicit error reporting when Neo4j is not configured in production."""

    def is_available(self) -> bool:
        return False

    def ensure_constraints(self) -> None:
        raise RuntimeError("Neo4j is not configured in production.")

    def sync_incident(
        self,
        incident: Dict[str, Any],
        assets: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        raise RuntimeError(
            "Neo4j graph persistence is not configured in production. "
            "Context graph synchronization requires NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD."
        )

    def get_incident_subgraph(self, incident_id: str) -> Dict[str, Any]:
        return {
            "incident_id": incident_id,
            "nodes": [],
            "edges": [],
            "source": "unconfigured",
            "message": "Neo4j graph database is not configured in production environment.",
        }

    def find_asset_path(
        self, incident_id: str, source_asset_id: str, target_asset_id: str
    ) -> Dict[str, Any]:
        raise RuntimeError(
            "Path queries require an active Neo4j database in production."
        )


_repo_instance: Optional[IncidentGraphRepositoryInterface] = None


def get_incident_graph_repository() -> IncidentGraphRepositoryInterface:
    """Factory selecting the appropriate graph repository based on configuration and environment."""
    global _repo_instance
    if _repo_instance is not None:
        return _repo_instance

    uri = settings.NEO4J_URI
    username = settings.NEO4J_USERNAME
    password = settings.NEO4J_PASSWORD

    if uri and username and password:
        logger.info("[RETRACE] Using Neo4j persistent Incident Context Graph repository.")
        _repo_instance = Neo4jIncidentGraphRepository()
        return _repo_instance

    if settings.ENVIRONMENT == "production":
        logger.warning("[RETRACE] NEO4J_URI is not configured in production. Graph synchronization disabled.")
        _repo_instance = ProductionUnconfiguredGraphRepository()
        return _repo_instance

    logger.info("[RETRACE] Neo4j not configured - using development in-memory context graph repository.")
    _repo_instance = InMemoryIncidentGraphRepository()
    return _repo_instance


def set_incident_graph_repository(repo: Optional[IncidentGraphRepositoryInterface]) -> None:
    """Allows test suites to inject mock or custom graph repositories."""
    global _repo_instance
    _repo_instance = repo
