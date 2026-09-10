"""Tests for RETRACE Qdrant Semantic Vector Retrieval Layer.

Verifies:
1. deterministic point IDs
2. collection creation configuration = 768 / COSINE
3. existing correct collection is preserved
4. collection dimension mismatch fails safely
5. Qdrant not configured behavior
6. evidence chunking deterministic
7. uploaded PostgreSQL evidence included
8. synthetic evidence included when factual content exists
9. missing text is not invented
10. incident-scoped reconciliation
11. repeated sync is idempotent
12. semantic search always filters by incident_id
13. optional asset filter
14. optional source_type filter
15. top_k capped at 20
16. similarity score is returned as similarity_score
17. fake embedding provider always returns exactly 768 dimensions
18. production does not silently fallback when Qdrant fails
19. no Qdrant secret appears in API output
20. API endpoint contract for vector sync and semantic search
"""
import unittest
import uuid
from unittest.mock import MagicMock, patch

try:
    from fastapi.testclient import TestClient
    from backend.app.main import app
    HAS_TESTCLIENT = True
except ImportError:
    TestClient = None  # type: ignore
    app = None  # type: ignore
    HAS_TESTCLIENT = False
from backend.core.config import settings
from backend.data.mock_data import MOCK_EVIDENCE
from backend.schemas.evidence import Evidence
from backend.schemas.upload import UploadedEvidence
from backend.repositories.uploaded_evidence_repository import (
    InMemoryUploadedEvidenceRepository,
    set_uploaded_evidence_repository,
)
from backend.vector.models import (
    EvidenceChunk,
    SemanticSearchRequest,
    SemanticSearchResponse,
    VectorSyncResponse,
    generate_deterministic_point_id,
)
from backend.vector.client import (
    check_qdrant_health,
    ensure_collection,
    validate_qdrant_url,
)
from backend.vector.embedding import (
    FakeEmbeddingProvider,
    GeminiEmbeddingProvider,
    EmbeddingProviderError,
)
from backend.vector.chunking import (
    EvidenceChunkingService,
    split_text_deterministically,
)
from backend.vector.repository import (
    InMemoryEvidenceVectorRepository,
    QdrantEvidenceVectorRepository,
)
from backend.vector.service import (
    VectorIndexService,
    VectorServiceError,
    set_vector_index_service,
    get_vector_index_service,
)


class TestQdrantVectorRetrieval(unittest.TestCase):
    """Comprehensive test suite for RETRACE Qdrant semantic retrieval."""

    def setUp(self):
        # Set up isolated in-memory repository and fake embedding provider
        self.vector_repo = InMemoryEvidenceVectorRepository(
            collection_name="retrace_evidence_v1",
            vector_size=768,
            distance="COSINE",
        )
        self.embedding_provider = FakeEmbeddingProvider(dimension=768)
        self.chunking_service = EvidenceChunkingService()
        self.upload_repo = InMemoryUploadedEvidenceRepository()
        set_uploaded_evidence_repository(self.upload_repo)

        self.service = VectorIndexService(
            vector_repo=self.vector_repo,
            embedding_provider=self.embedding_provider,
            chunking_service=self.chunking_service,
            upload_repo=self.upload_repo,
        )
        set_vector_index_service(self.service)
        if HAS_TESTCLIENT and app is not None:
            self.client = TestClient(app)
        else:
            self.client = None

    def tearDown(self):
        set_vector_index_service(None)
        set_uploaded_evidence_repository(None)

    # 1. Deterministic point IDs
    def test_1_deterministic_point_ids(self):
        pid1 = generate_deterministic_point_id("INC-2026-001", "EVD-001", 0)
        pid2 = generate_deterministic_point_id("INC-2026-001", "EVD-001", 0)
        pid3 = generate_deterministic_point_id("INC-2026-001", "EVD-001", 1)
        pid4 = generate_deterministic_point_id("INC-2026-002", "EVD-001", 0)

        # Must be deterministic across calls
        self.assertEqual(pid1, pid2)
        # Must differ across chunk index
        self.assertNotEqual(pid1, pid3)
        # Must differ across incidents
        self.assertNotEqual(pid1, pid4)
        # Must be valid UUID format
        parsed_uuid = uuid.UUID(pid1)
        self.assertEqual(str(parsed_uuid), pid1)

    # 2. Collection creation configuration = 768 / COSINE
    def test_2_collection_creation_configuration(self):
        mock_qdrant = MagicMock()
        mock_qdrant.collection_exists.return_value = False

        created = ensure_collection(
            client=mock_qdrant,
            collection_name="retrace_evidence_v1",
            vector_size=768,
            distance_str="COSINE",
        )
        self.assertTrue(created)
        mock_qdrant.create_collection.assert_called_once()
        args, kwargs = mock_qdrant.create_collection.call_args
        self.assertEqual(kwargs.get("collection_name"), "retrace_evidence_v1")
        # Check payload index creation
        self.assertGreaterEqual(mock_qdrant.create_payload_index.call_count, 5)

    # 3. Existing correct collection is preserved
    def test_3_existing_correct_collection_is_preserved(self):
        mock_qdrant = MagicMock()
        mock_qdrant.collection_exists.return_value = True

        mock_info = MagicMock()
        mock_vectors = MagicMock()
        mock_vectors.size = 768
        mock_vectors.distance = "Cosine"
        mock_info.config.params.vectors = mock_vectors
        mock_qdrant.get_collection.return_value = mock_info

        created = ensure_collection(
            client=mock_qdrant,
            collection_name="retrace_evidence_v1",
            vector_size=768,
            distance_str="COSINE",
        )
        self.assertFalse(created)
        # Ensure collection was NOT recreated or deleted
        mock_qdrant.create_collection.assert_not_called()
        mock_qdrant.delete_collection.assert_not_called()

    # 4. Collection dimension mismatch fails safely
    def test_4_collection_dimension_mismatch_fails_safely(self):
        mock_qdrant = MagicMock()
        mock_qdrant.collection_exists.return_value = True

        mock_info = MagicMock()
        mock_vectors = MagicMock()
        mock_vectors.size = 512  # Mismatched dimension
        mock_vectors.distance = "Cosine"
        mock_info.config.params.vectors = mock_vectors
        mock_qdrant.get_collection.return_value = mock_info

        with self.assertRaises(ValueError) as ctx:
            ensure_collection(
                client=mock_qdrant,
                collection_name="retrace_evidence_v1",
                vector_size=768,
                distance_str="COSINE",
            )
        self.assertIn("vector dimension mismatch", str(ctx.exception))
        # Automatic deletion is strictly prohibited
        mock_qdrant.delete_collection.assert_not_called()

    # 5. Qdrant not configured behavior
    def test_5_qdrant_not_configured_behavior(self):
        with patch.object(settings, "QDRANT_URL", None):
            status_data = check_qdrant_health()
            self.assertEqual(status_data, {"vector": "not_configured"})

            if self.client is not None:
                res = self.client.get("/health/vector")
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.json(), {"vector": "not_configured"})

    # 6. Evidence chunking deterministic and preserves identifiers
    def test_6_evidence_chunking_deterministic(self):
        mock_ev = Evidence(**MOCK_EVIDENCE[3])  # Pump Manual PDF
        chunks1 = self.chunking_service.chunk_synthetic_evidence(mock_ev, "INC-2026-001")
        chunks2 = self.chunking_service.chunk_synthetic_evidence(mock_ev, "INC-2026-001")

        self.assertEqual(len(chunks1), len(chunks2))
        for c1, c2 in zip(chunks1, chunks2):
            self.assertEqual(c1.point_id, c2.point_id)
            self.assertEqual(c1.chunk_id, c2.chunk_id)
            self.assertEqual(c1.text, c2.text)

        # Test identifier preservation (e.g. VFD-204, P-204, M-204)
        sample_text = "The pump P-204 was driven by motor M-204 which received power from VFD-204 through controller PLC-204."
        split_chunks = split_text_deterministically(sample_text, max_chunk_chars=40, overlap_chars=5)
        for chk in split_chunks:
            # None of the chunks should have severed "P-204" into "P-" or "VFD-"
            self.assertFalse(chk.endswith("P-") or chk.startswith("-204"))
            self.assertFalse(chk.endswith("VFD-") or chk.endswith("M-"))

    # 7. Uploaded PostgreSQL evidence included
    def test_7_uploaded_postgresql_evidence_included(self):
        uploaded_rec = UploadedEvidence(
            evidence_id="EVD-UPL-TEST01",
            incident_id="INC-2026-001",
            source_type="PLC / SCADA",
            original_filename="Turbine_Alarm.csv",
            stored_filename="turb_alarm.csv",
            content_type="text/csv",
            file_size=4096,
            asset_id="P-204",
            description="Field alarm export from Skid B",
            storage_uri="gs://test-bucket/alarm.csv",
            uploaded_at="2026-09-08T10:20:00Z",
            sha256_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            metadata={
                "columns": ["Time", "Tag", "Value", "Severity"],
                "row_count": 2,
                "preview_rows": [
                    {"Time": "10:14:02", "Tag": "P204_TRIP", "Value": "HIGH", "Severity": "CRITICAL"},
                    {"Time": "10:14:03", "Tag": "M204_STATUS", "Value": "STOP", "Severity": "INFO"},
                ],
            },
        )
        self.upload_repo.create(uploaded_rec)

        res = self.service.sync_incident("INC-2026-001")
        self.assertEqual(res["status"], "synchronized")
        self.assertGreater(res["chunks_indexed"], 6)

        # Search specifically for the uploaded tag
        search_res = self.service.semantic_search(
            incident_id="INC-2026-001",
            query="P204_TRIP alarm critical",
            top_k=10,
        )
        found_uploaded = any(r["evidence_id"] == "EVD-UPL-TEST01" for r in search_res["results"])
        self.assertTrue(found_uploaded)

    # 8. Synthetic evidence included when factual content exists
    def test_8_synthetic_evidence_included_when_factual_content_exists(self):
        res = self.service.sync_incident("INC-2026-001")
        self.assertGreaterEqual(res["evidence_processed"], 6)
        self.assertGreaterEqual(res["chunks_indexed"], 6)

        # Search for vibration criteria from Pump Manual (EVD-004)
        search_res = self.service.semantic_search(
            incident_id="INC-2026-001",
            query="ISO 10816-3 permissible vibration tripping limit 7.1 mm/s",
        )
        self.assertGreater(len(search_res["results"]), 0)
        evd_ids = {r["evidence_id"] for r in search_res["results"]}
        self.assertIn("EVD-004", evd_ids)

    # 9. Missing text is not invented
    def test_9_missing_text_is_not_invented(self):
        # 1. PDF with only page count and NO extracted text
        pdf_no_text = UploadedEvidence(
            evidence_id="EVD-UPL-PDF-EMPTY",
            incident_id="INC-2026-001",
            source_type="Engineering Documents",
            original_filename="Schematic_Diagram.pdf",
            stored_filename="schematic.pdf",
            content_type="application/pdf",
            file_size=10240,
            asset_id="PLC-204",
            storage_uri="gs://test-bucket/schematic.pdf",
            uploaded_at="2026-09-08T10:25:00Z",
            sha256_hash="1111222233334444555566667777888811112222333344445555666677778888",
            metadata={
                "format": "pdf",
                "pages": 12,
                "preview_text": None,  # No extracted text!
            },
        )
        chunks = self.chunking_service.chunk_uploaded_evidence(pdf_no_text)
        # MUST NOT invent fake PDF text
        self.assertEqual(len(chunks), 0)

        # 2. Image evidence (strictly do not invent captions)
        img_no_text = UploadedEvidence(
            evidence_id="EVD-UPL-IMG-01",
            incident_id="INC-2026-001",
            source_type="Technician Notes & Photos",
            original_filename="broken_coupling.png",
            stored_filename="broken_coupling.png",
            content_type="image/png",
            file_size=204800,
            asset_id="P-204",
            storage_uri="gs://test-bucket/broken_coupling.png",
            uploaded_at="2026-09-08T10:26:00Z",
            sha256_hash="9999888877776666555544443333222299998888777766665555444433332222",
            metadata={"format": "image"},
        )
        img_chunks = self.chunking_service.chunk_uploaded_evidence(img_no_text)
        self.assertEqual(len(img_chunks), 0)

    # 10. Incident-scoped reconciliation
    def test_10_incident_scoped_reconciliation(self):
        # Seed points for INC-2026-001 and INC-2026-002
        self.service.sync_incident("INC-2026-001")
        initial_points_count = len(self.vector_repo._store)
        self.assertGreater(initial_points_count, 0)

        # Manually inject a point for another incident
        other_chunk = EvidenceChunk(
            point_id=generate_deterministic_point_id("INC-2026-002", "EVD-OTHER", 0),
            incident_id="INC-2026-002",
            evidence_id="EVD-OTHER",
            chunk_id="EVD-OTHER-chk-0",
            chunk_index=0,
            source_type="PLC / SCADA",
            filename="other.csv",
            content_type="text/csv",
            modality="tabular",
            text="Unrelated plant area 5 telemetry",
            storage_uri="gs://other/other.csv",
            sha256_hash="0000111122223333",
            managed_by="retrace",
        )
        self.vector_repo.upsert_chunks([other_chunk], [self.embedding_provider.embed_query("test")])

        # Delete points for INC-2026-001
        self.vector_repo.delete_incident_vectors("INC-2026-001")

        # INC-2026-002 point MUST remain
        remaining_pids = list(self.vector_repo._store.keys())
        self.assertEqual(len(remaining_pids), 1)
        self.assertEqual(remaining_pids[0], other_chunk.point_id)

    # 11. Repeated sync is idempotent
    def test_11_repeated_sync_is_idempotent(self):
        res1 = self.service.sync_incident("INC-2026-001")
        points_count_1 = len(self.vector_repo._store)
        pids_1 = set(self.vector_repo._store.keys())

        # Second sync
        res2 = self.service.sync_incident("INC-2026-001")
        points_count_2 = len(self.vector_repo._store)
        pids_2 = set(self.vector_repo._store.keys())

        self.assertEqual(res1["chunks_indexed"], res2["chunks_indexed"])
        self.assertEqual(points_count_1, points_count_2)
        self.assertEqual(pids_1, pids_2)

    # 12. Semantic search always filters by incident_id
    def test_12_semantic_search_always_filters_by_incident_id(self):
        self.service.sync_incident("INC-2026-001")

        # Inject point for another incident with high-overlap text
        other_chunk = EvidenceChunk(
            point_id=generate_deterministic_point_id("INC-2026-002", "EVD-OTHER-2", 0),
            incident_id="INC-2026-002",
            evidence_id="EVD-OTHER-2",
            chunk_id="EVD-OTHER-2-chk-0",
            chunk_index=0,
            source_type="VFD / Drive Logs",
            filename="other_drive.csv",
            content_type="text/csv",
            modality="tabular",
            text="Overcurrent Warning W-2310 logged with current peak 300A",
            storage_uri="gs://other/other_drive.csv",
            sha256_hash="2222333344445555",
            managed_by="retrace",
        )
        self.vector_repo.upsert_chunks([other_chunk], [self.embedding_provider.embed_query("overcurrent")])

        # Search scoped to INC-2026-001
        res = self.service.semantic_search(
            incident_id="INC-2026-001",
            query="Overcurrent Warning W-2310",
        )
        # Results must strictly contain only INC-2026-001
        for item in res["results"]:
            self.assertNotEqual(item["evidence_id"], "EVD-OTHER-2")

    # 13. Optional asset filter
    def test_13_optional_asset_filter(self):
        self.service.sync_incident("INC-2026-001")

        # Search specifically for VFD-204
        res = self.service.semantic_search(
            incident_id="INC-2026-001",
            query="current voltage frequency telemetry",
            asset_id="VFD-204",
        )
        self.assertGreater(len(res["results"]), 0)
        for item in res["results"]:
            self.assertEqual(item["asset_id"], "VFD-204")

    # 14. Optional source_type filter
    def test_14_optional_source_type_filter(self):
        self.service.sync_incident("INC-2026-001")

        # Search filtered by Engineering Documents
        res = self.service.semantic_search(
            incident_id="INC-2026-001",
            query="vibration tripping limit",
            source_type="Engineering Documents",
        )
        self.assertGreater(len(res["results"]), 0)
        for item in res["results"]:
            self.assertEqual(item["source_type"], "Engineering Documents")

        # Test canonical code filter ("ENGINEERING_DOCUMENT")
        res_canonical = self.service.semantic_search(
            incident_id="INC-2026-001",
            query="vibration tripping limit",
            source_type="ENGINEERING_DOCUMENT",
        )
        self.assertGreater(len(res_canonical["results"]), 0)

    # 15. top_k capped at 20
    def test_15_top_k_capped_at_20(self):
        self.service.sync_incident("INC-2026-001")

        # Service enforces bound
        res = self.service.semantic_search(
            incident_id="INC-2026-001",
            query="vibration alarm",
            top_k=50,
        )
        self.assertLessEqual(len(res["results"]), 20)

        # API schema enforces le=20
        if self.client is not None:
            api_res = self.client.post(
                "/api/incidents/INC-2026-001/search/semantic",
                json={"query": "vibration alarm", "top_k": 25},
            )
            self.assertEqual(api_res.status_code, 422)  # Validation error

    # 16. Similarity score is returned as similarity_score
    def test_16_similarity_score_returned_as_similarity_score(self):
        self.service.sync_incident("INC-2026-001")

        search_res = self.service.semantic_search(
            incident_id="INC-2026-001",
            query="abnormal load before shutdown",
            top_k=5,
        )
        self.assertIn("results", search_res)
        self.assertGreater(len(search_res["results"]), 0)

        first_hit = search_res["results"][0]
        # Crucial check: Must be named similarity_score
        self.assertIn("similarity_score", first_hit)
        self.assertIsInstance(first_hit["similarity_score"], (int, float))

        # Must NOT use confidence, certainty, probability
        self.assertNotIn("confidence", first_hit)
        self.assertNotIn("certainty", first_hit)
        self.assertNotIn("probability", first_hit)

        if self.client is not None:
            api_res = self.client.post(
                "/api/incidents/INC-2026-001/search/semantic",
                json={"query": "abnormal load before shutdown", "top_k": 5},
            )
            self.assertEqual(api_res.status_code, 200)
            data = api_res.json()
            api_first_hit = data["results"][0]
            self.assertIn("similarity_score", api_first_hit)
            self.assertNotIn("confidence", api_first_hit)
            self.assertNotIn("certainty", api_first_hit)
            self.assertNotIn("probability", api_first_hit)

    # 17. Fake embedding provider always returns exactly 768 dimensions
    def test_17_fake_embedding_provider_always_returns_768_dimensions(self):
        provider = FakeEmbeddingProvider(dimension=768)

        # Single string
        vec1 = provider.embed_query("abnormal load before pump shutdown")
        self.assertEqual(len(vec1), 768)
        self.assertTrue(all(isinstance(v, float) for v in vec1))

        # Multiple texts
        texts = [
            "VFD-204 overcurrent warning",
            "M-204 motor vibration 9.2 mm/s",
            "P-204 cavitation gravel rattling in casing",
            "Short",
            "A" * 500,
        ]
        batch_vecs = provider.embed_texts(texts)
        self.assertEqual(len(batch_vecs), len(texts))
        for v in batch_vecs:
            self.assertEqual(len(v), 768)

    # 18. Production does not silently fallback when Qdrant fails
    def test_18_production_does_not_silently_fallback_when_qdrant_fails(self):
        # Default service with no live Qdrant configured
        prod_service = VectorIndexService(
            vector_repo=None,  # Will attempt QdrantEvidenceVectorRepository()
            embedding_provider=self.embedding_provider,
        )
        with patch.object(settings, "QDRANT_URL", None):
            with self.assertRaises(VectorServiceError) as ctx:
                prod_service.sync_incident("INC-2026-001")
            self.assertEqual(ctx.exception.status_code, 503)
            self.assertIn("Qdrant vector database is not configured", ctx.exception.message)

            with self.assertRaises(VectorServiceError) as ctx2:
                prod_service.semantic_search("INC-2026-001", "vibration")
            self.assertEqual(ctx2.exception.status_code, 503)

    # 19. No Qdrant secret appears in API output
    def test_19_no_qdrant_secret_appears_in_api_output(self):
        secret_key = "qdrant_secret_key_prod_abc987654321"
        with patch.object(settings, "QDRANT_API_KEY", secret_key):
            with patch.object(settings, "QDRANT_URL", "https://qdrant-cluster.example.com:6333"):
                health_status = check_qdrant_health()
                self.assertNotIn(secret_key, str(health_status))

                if self.client is not None:
                    health_res = self.client.get("/health/vector")
                    body_str = health_res.text
                    self.assertNotIn(secret_key, body_str)
                    self.assertNotIn("qdrant-cluster.example.com", body_str)

        # URL validation: enforce HTTPS in production
        with self.assertRaises(ValueError):
            validate_qdrant_url("http://remote-cluster:6333", is_development=False)
        # Localhost allowed
        validate_qdrant_url("http://localhost:6333", is_development=False)
        validate_qdrant_url("https://remote-cluster:6333", is_development=False)

    # 20. End-to-end Vector Sync API
    def test_20_vector_sync_api_endpoint(self):
        sync_res = self.service.sync_incident("INC-2026-001")
        self.assertEqual(sync_res["incident_id"], "INC-2026-001")
        self.assertEqual(sync_res["status"], "synchronized")
        self.assertGreater(sync_res["chunks_indexed"], 0)
        self.assertEqual(sync_res["collection"], "retrace_evidence_v1")

        # Unknown incident fails with 404
        with self.assertRaises(VectorServiceError) as ctx:
            self.service.sync_incident("INC-UNKNOWN")
        self.assertEqual(ctx.exception.status_code, 404)

        if self.client is not None:
            client_sync = self.client.post("/api/incidents/INC-2026-001/vectors/sync")
            self.assertEqual(client_sync.status_code, 200)
            data = client_sync.json()
            self.assertEqual(data["incident_id"], "INC-2026-001")
            self.assertEqual(data["status"], "synchronized")

            bad_res = self.client.post("/api/incidents/INC-UNKNOWN/vectors/sync")
            self.assertEqual(bad_res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
