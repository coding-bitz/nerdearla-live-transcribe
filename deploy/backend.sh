#!/usr/bin/env bash
set -euo pipefail

echo "=== Deploying Backend to Google Cloud Run ==="

# 1. Verify gcloud CLI
if ! command -v gcloud &> /dev/null; then
  echo "Error: gcloud CLI is not installed. Please install Google Cloud SDK." >&2
  exit 1
fi

# 2. Check GCP Project
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
if [ -z "${PROJECT_ID}" ]; then
  echo "Error: GOOGLE_CLOUD_PROJECT is not set and no active gcloud project found." >&2
  echo "Run: gcloud config set project YOUR_PROJECT_ID" >&2
  exit 1
fi
echo "Using GCP Project: ${PROJECT_ID}"

REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE_NAME="nerdearla-subtitles-backend"
SA_NAME="nerdearla-subtitles"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# 3. Check Authentication
echo "Checking gcloud authentication..."
gcloud auth print-access-token > /dev/null

# 4. Enable Required APIs
echo "Ensuring required GCP APIs are enabled..."
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  --project "${PROJECT_ID}"

# 5. Service Account Setup
echo "Verifying dedicated Service Account..."
if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project "${PROJECT_ID}" &> /dev/null; then
  echo "Creating service account ${SA_NAME}..."
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="Nerdearla Live Subtitles" \
    --project "${PROJECT_ID}"
fi

echo "Ensuring minimal IAM role (roles/aiplatform.user) is granted..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user" \
  --condition=None \
  --quiet > /dev/null

# 6. Deploy to Cloud Run
echo "Deploying ${SERVICE_NAME} to Cloud Run in ${REGION}..."
gcloud run deploy "${SERVICE_NAME}" \
  --source ./backend \
  --region "${REGION}" \
  --platform managed \
  --service-account "${SA_EMAIL}" \
  --timeout 3600 \
  --cpu 1 \
  --memory 1Gi \
  --min-instances 0 \
  --max-instances 10 \
  --session-affinity \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=global,ENVIRONMENT=production" \
  --project "${PROJECT_ID}"

# 7. Retrieve Service URL and verify Health Check
BACKEND_URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --project "${PROJECT_ID}" --format="value(status.url)")
echo "Backend deployed at: ${BACKEND_URL}"

echo "Testing /health endpoint..."
HEALTH_RESPONSE=$(curl -fsS "${BACKEND_URL}/health" || echo "FAIL")
if [[ "${HEALTH_RESPONSE}" == *"\"status\":\"ok\""* || "${HEALTH_RESPONSE}" == *"\"status\": \"ok\""* ]]; then
  echo "Backend health check passed successfully."
else
  echo "Warning: Health check did not return status ok: ${HEALTH_RESPONSE}" >&2
fi

echo "=== Backend Deployment Complete ==="
