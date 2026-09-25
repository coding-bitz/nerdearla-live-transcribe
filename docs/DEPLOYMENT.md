# Deployment Guide

This guide covers running Nerdearla Live Subtitles locally with Docker, in development mode, and deploying to Google Cloud Run with Application Default Credentials (ADC).

---

## 1. Prerequisites

* **Google Cloud SDK (`gcloud`)** installed and authenticated.
* A Google Cloud Project with the following APIs enabled:
  * `run.googleapis.com` (Cloud Run)
  * `aiplatform.googleapis.com` (Vertex AI / Agent Platform)
  * `artifactregistry.googleapis.com` (Container Storage)
* **Docker** and **Docker Compose** installed (for local containerized testing).
* **Node.js 20+** and **Python 3.12+** (for manual local development).

---

## 2. Local Development Setup

### 2.1 Set Up Application Default Credentials (ADC)
In your local terminal, login using ADC so the official `google-genai` client can authenticate with your project:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
export GOOGLE_CLOUD_LOCATION=global
```

### 2.2 Run with Docker Compose
To launch the complete stack (Backend, Frontend, and Redis services):

```bash
docker compose up --build
```

Endpoints:
* **Frontend Application**: `http://localhost:5173`
* **Backend Health Check**: `curl -fsS http://localhost:8080/health` (HTTP 200 `{"status":"ok"}`)
* **Backend Readiness Check**: `curl -i http://localhost:8080/ready` (HTTP 200 with Redis connected; HTTP 503 if Redis is down)
* **Redis Store**: `localhost:6379`

### 2.3 Run the Frontend
In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to test live microphone capture and WebSocket streaming.

---

## 3. Google Cloud Run Deployment

Deployment to Google Cloud Run uses dedicated Service Accounts with minimal IAM permissions and native WebSocket configurations.

### 3.1 Automated Deployment
Run the automated deployment script from the project root:

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_REGION=us-central1

./deploy/deploy.sh
```

### 3.2 Manual Cloud Run Setup & Commands

#### Step A: Create Dedicated Service Account
```bash
gcloud iam service-accounts create nerdearla-subtitles \
  --display-name="Nerdearla Live Subtitles" \
  --project="${GOOGLE_CLOUD_PROJECT}"
```

#### Step B: Grant AI Platform Access
Assign the verified role required for calling generative models:

```bash
gcloud projects add-iam-policy-binding "${GOOGLE_CLOUD_PROJECT}" \
  --member="serviceAccount:nerdearla-subtitles@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

#### Step C: Deploy Backend Service
```bash
gcloud run deploy nerdearla-subtitles-backend \
  --source ./backend \
  --region us-central1 \
  --platform managed \
  --service-account="nerdearla-subtitles@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
  --timeout=3600 \
  --cpu=1 \
  --memory=1Gi \
  --min-instances=0 \
  --max-instances=10 \
  --session-affinity \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=global,ENVIRONMENT=production"
```

*Note on WebSocket Timeout:* Cloud Run requires an explicit `--timeout` (up to 3600 seconds) to ensure long-lived WebSocket connections are not terminated prematurely.

#### Step D: Verify Deployment Health
```bash
BACKEND_URL=$(gcloud run services describe nerdearla-subtitles-backend --region us-central1 --format="value(status.url)")
curl -fsS "${BACKEND_URL}/health"
```
Output:
```json
{"status":"ok"}
```

---

## 4. Security & Production Checklist

1. **No Runtime API Keys**: Never inject `GOOGLE_CLOUD_API_KEY` into Cloud Run. Credential authentication is handled automatically by ADC.
2. **Frontend Boundaries**: No cloud secrets, private keys, or tokens are bundled into frontend assets.
3. **CORS Restrictions**: Set `FRONTEND_URL` in Cloud Run environment variables to restrict origins in production.
