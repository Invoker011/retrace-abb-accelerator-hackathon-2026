# RETRACE Backend — Multimodal Industrial Maintenance Intelligence

Backend service for **RETRACE**, an industrial incident investigation and multimodal maintenance intelligence prototype developed for the ABB Accelerator 2026 Hackathon (Theme 2).

RETRACE reconstructs industrial incidents from fragmented operational, engineering, visual, maintenance, and technician evidence and assists technicians in troubleshooting equipment anomalies.

> **Industrial Safety Advisory**: RETRACE is strictly an advisory decision-support system. It never directly controls machinery, overrides interlocks, or executes maintenance actions autonomously. All insights require human engineering judgment.

---

## Architecture & Directory Layout

```
backend/
├── app/
│   ├── main.py               # FastAPI application entry point and middleware configuration
│   ├── api/                  # API routers (incidents, evidence, investigation)
│   ├── core/                 # Environment and application settings
│   ├── data/                 # Synthetic incident dataset (INC-2026-001)
│   ├── models/               # Domain model definitions
│   ├── schemas/              # Pydantic validation schemas
│   └── services/             # Deterministic intelligence and incident services
├── tests/
│   ├── __init__.py
│   └── test_api.py           # Endpoint integration and validation tests
├── Dockerfile                # Container definition for Google Cloud Run
├── .dockerignore             # Docker build context exclusions
├── CLOUD_RUN_DEPLOY.md       # Google Cloud Run deployment guide and gcloud commands
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable documentation
└── README.md
```

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
