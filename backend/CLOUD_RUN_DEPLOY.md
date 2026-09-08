# Deploying RETRACE Backend to Google Cloud Run

This guide provides step-by-step instructions and exact Google Cloud CLI (`gcloud`) commands to deploy the RETRACE FastAPI intelligence backend to Google Cloud Run.

---

## Prerequisites

1. Install and authenticate the Google Cloud CLI:
   ```bash
   gcloud auth login
   ```
2. Have a Google Cloud project with billing enabled.

---

## Deployment Steps

### 1. Select Your Google Cloud Project

Set your active Google Cloud project ID (replace `YOUR_PROJECT_ID` with your actual project ID):

```bash
gcloud config set project YOUR_PROJECT_ID
```

*(Optional) Verify the active project:*
```bash
gcloud config get-value project
```

---

### 2. Enable Required Google Cloud APIs

Enable the Cloud Run and Cloud Build APIs:

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

---

### 3. Deploy the Backend from the `backend/` Directory

Navigate into the `backend/` directory and deploy the service.

> **Service Name**: `retrace-api`  
> **Default Region**: `us-central1` (you may replace with your preferred region)  
> **Access**: `--allow-unauthenticated` for this hackathon prototype

```bash
cd backend

gcloud run deploy retrace-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production
```

> **Note on CORS**: If you know your Google AI Studio frontend URL (for example `https://ais-dev-...run.app`), you can optionally include it in `CORS_ORIGINS` during deployment or update it at any time:
> ```bash
> gcloud run services update retrace-api \
>   --region us-central1 \
>   --update-env-vars CORS_ORIGINS="YOUR_FRONTEND_URL,http://localhost:3000"
> ```

---

### 4. Obtain the Resulting Cloud Run Service URL

Retrieve the HTTPS URL assigned to the deployed service:

```bash
SERVICE_URL=$(gcloud run services describe retrace-api --region us-central1 --format='value(status.url)')
echo "RETRACE API URL: $SERVICE_URL"
```

The output will look similar to:
```
https://retrace-api-xxxxx.run.app
```

---

### 5. Verify the Deployed Service

#### Test the `/health` Endpoint

```bash
curl -s "$SERVICE_URL/health"
```

**Expected Response:**
```json
{"status":"healthy","service":"RETRACE API"}
```

#### Test the Incident Context Endpoint

```bash
curl -s "$SERVICE_URL/api/incidents/INC-2026-001/context"
```

**Expected Response:**
A JSON payload containing the complete incident context:
```json
{
  "incident": {"id": "INC-2026-001", "title": "Pump P-204 Cavitation & Trip", ...},
  "events": [...],
  "assets": [...],
  "relationships": [...],
  "evidence": [...],
  "findings": [...]
}
```

---

## Connecting Frontend to the Cloud Run Backend

Once your Cloud Run service is active and you have the service URL:

1. Open **Settings** in your AI Studio project.
2. Under Environment Variables, set:
   ```env
   VITE_RETRACE_API_URL=https://retrace-api-xxxxx.run.app
   ```
   *(Replace with your actual Cloud Run service URL)*

> **Critical Note on URL Format**:  
> **Do NOT add `/api` at the end of the URL.**  
> The frontend `apiClient.ts` expects the base origin (e.g. `https://retrace-api-xxxxx.run.app`) and dynamically appends routes like `/health` and `/api/incidents/...`.
