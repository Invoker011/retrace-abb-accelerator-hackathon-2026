# RETRACE Backend — Multimodal Industrial Maintenance Intelligence

Backend service for **RETRACE**, an industrial incident investigation and multimodal maintenance intelligence prototype developed for the ABB Accelerator 2026 Hackathon (Theme 2).

RETRACE reconstructs industrial incidents from fragmented operational, engineering, visual, maintenance, and technician evidence and assists technicians in troubleshooting equipment anomalies.

> **Industrial Safety Advisory**: RETRACE is strictly an advisory decision-support system. It never directly controls machinery, overrides interlocks, or executes maintenance actions autonomously. All insights require human engineering judgment.

---

## Architecture & Directory Layout

```
backend/
├── alembic/                  # Database schema migrations
│   ├── env.py                # Dynamic DATABASE_URL configuration
│   ├── script.py.mako        # Migration template
│   └── versions/             # Migration scripts
│       └── 001_create_uploaded_evidence_table.py
├── alembic.ini               # Alembic configuration file
├── app/
│   ├── main.py               # FastAPI application entry point and health checks
├── database/                 # Relational database layer
│   ├── models.py             # SQLAlchemy 2.0 models (UploadedEvidenceModel)
│   └── session.py            # Engine, sessionmaker, and connectivity checks
├── repositories/             # Repository pattern layer
│   └── uploaded_evidence_repository.py  # PostgreSQL & fallback repositories
├── services/                 # Industrial intelligence & ingestion services
│   ├── evidence_storage.py   # Immutable raw file storage (GCS & Local)
│   ├── upload_service.py     # Upload orchestration & consistency rollback
│   └── evidence_extractor.py # Deterministic non-AI metadata extraction
├── schemas/                  # Pydantic schemas (UploadedEvidence, Incident)
├── tests/                    # Unit and integration test suite
├── requirements.txt          # Python dependencies (FastAPI, SQLAlchemy, Alembic, psycopg)
├── .env.example              # Environment variable documentation
└── README.md
```

---

## Industrial Evidence Storage & Persistence Architecture

RETRACE separates raw file storage from metadata indexing using a dual-layer architecture:

1. **Immutable Raw Evidence Storage (Google Cloud Storage / Local Filesystem)**:
   - Binary evidence payloads (CSV logs, PDFs, images, text records) are stored immutably.
   - Identified by server-generated unique IDs: `EVD-UPL-{UUID}_{safe_filename}`.
   - Configured via `GCS_BUCKET_NAME`.

2. **Durable Evidence Metadata & Provenance (PostgreSQL via SQLAlchemy 2.x)**:
   - Persists evidence provenance records in the `uploaded_evidence` table:
     - `evidence_id`, `incident_id`, `source_type`, `original_filename`, `stored_filename`, `content_type`, `file_size`, `asset_id`, `description`, `storage_uri`, `uploaded_at`, `processing_status`, `sha256_hash`, `metadata`.
   - Indexed on `incident_id`, `asset_id`, `source_type`, `processing_status`, `sha256_hash`, and `uploaded_at`.
   - Managed with Alembic migrations.

3. **Consistency & Orphan Cleanup**:
   - If raw file storage succeeds but database metadata insertion fails, RETRACE automatically attempts deletion of the newly stored object so orphaned files are not left behind.
   - Database operations are encapsulated behind `UploadedEvidenceRepositoryInterface`.

4. **Environment Fallback Behavior**:
   - **Development Mode (`ENVIRONMENT=development`)**:
     If `DATABASE_URL` is unset, backend falls back to an in-memory repository for local development and logs:
     `[RETRACE] PostgreSQL not configured - using development in-memory metadata repository`.
   - **Production Mode (`ENVIRONMENT=production`)**:
     If `DATABASE_URL` is unset, RETRACE enforces durable storage and rejects uploads with an explicit 500 configuration error rather than silently pretending evidence was saved. Non-upload endpoints continue working normally.

---

## Database Migrations (Alembic)

Run migrations to create or update the PostgreSQL database schema:

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback latest migration
alembic downgrade -1
```

`alembic/env.py` dynamically sources `DATABASE_URL` from server environment variables; connection strings and credentials are never stored in `alembic.ini`.

---

## Getting Started

### 1. Prerequisites
- Python 3.10 or newer
- `pip` and virtual environment support (`venv`)

### 2. Environment Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy the environment example file:

```bash
cp .env.example .env
```

### 3. Running the Development Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- Base URL: `http://localhost:8000`
- Interactive OpenAPI Swagger UI: `http://localhost:8000/docs`
- ReDoc Documentation: `http://localhost:8000/redoc`

### 4. Running Tests

```bash
pytest tests/
```

---

## API Endpoints

### Health Check
- `GET /health`: Returns service health status `{"status": "healthy", "service": "RETRACE API"}`

### Incident Endpoints
- `GET /api/incidents`: List all industrial incidents.
- `GET /api/incidents/{incident_id}`: Retrieve incident overview (e.g., `INC-2026-001`).
- `GET /api/incidents/{incident_id}/events`: Retrieve normalized timeline events in chronological sequence.
- `GET /api/incidents/{incident_id}/assets`: Retrieve mechanical and electrical assets involved in the incident (`VFD-204`, `M-204`, `P-204`, `PLC-204`).
- `GET /api/incidents/{incident_id}/relationships`: Retrieve asset topology relationships (`powers`, `drives`, `monitored by`).
- `GET /api/incidents/{incident_id}/findings`: Retrieve investigation findings with strict classification (`OBSERVED`, `CORRELATED`, `HYPOTHESIS`, `UNKNOWN`).
- `GET /api/incidents/{incident_id}/evidence`: Retrieve all evidence artifacts connected to the incident.
- `GET /api/incidents/{incident_id}/context`: Combined incident context payload containing incident, timeline events, assets, topology, evidence, and findings.
- `GET /api/incidents/{incident_id}/prevention`: Counterfactual prevention scenario (`actual_path`, `possible_intervention_path`, `safeguards`) with mandatory disclaimer:
  > *"This is an exploratory prevention scenario. RETRACE does not claim that the proposed intervention would definitely have prevented the incident."*

### Evidence & Provenance Endpoints
- `GET /api/evidence/{evidence_id}`: Retrieve detailed provenance record for an evidence artifact (source type, confidence score, raw archive location, normalized timestamp, preview rows).

### Technician Troubleshooting Assistant
- `POST /api/investigation/query`:
  Deterministic investigation assistant returning grounded answers, findings, supporting evidence, classification, and unresolved questions.

  **Request Body:**
  ```json
  {
    "incident_id": "INC-2026-001",
    "question": "Why did Pump P-204 shut down?"
  }
  ```

  **Response:**
  ```json
  {
    "answer": "The available evidence shows that VFD-204 recorded an overcurrent warning 27 seconds before the PLC shutdown alarm. Motor M-204 current deviation and Pump P-204 process disturbance followed. These events are temporally correlated across physically related assets, but the available evidence does not confirm the exact mechanical root cause.",
    "findings": [...],
    "supporting_evidence": [...],
    "classification": "CORRELATED",
    "unresolved_questions": [
      "What caused the instantaneous overcurrent peak in VFD-204 at 10:14:01?",
      "Was there physical mechanical binding in pump P-204 or an upstream electrical surge?",
      "What was the suction strainer differential pressure prior to cavitation onset?"
    ],
    "suggested_follow_ups": [
      "What happened before the shutdown?",
      "Which assets were involved?",
      "What evidence supports this finding?",
      "What should the technician inspect next?",
      "What information is still missing?"
    ]
  }
  ```

---

## Grounding & Provenance Principles

1. **Strict Epistemic Classification**:
   - `OBSERVED`: Supported directly by timestamped logs and sensor records.
   - `CORRELATED`: Temporal or topological correlation across assets, but not proven causal.
   - `HYPOTHESIS`: Plausible technical deduction requiring physical inspection to confirm.
   - `UNKNOWN`: Information missing from available evidence (e.g., high-frequency vibration FFT, internal pump condition).

2. **Immutable Provenance**:
   - Every piece of evidence maintains its original source, row/offset reference, sensor tag, original timestamp, normalized ISO-8601 timestamp, and confidence rating.
