#!/usr/bin/env bash
set -euo pipefail

echo "=== Deploying Frontend to Google Cloud Run ==="

# 1. Verify gcloud CLI
if ! command -v gcloud &> /dev/null; then
  echo "Error: gcloud CLI is not installed." >&2
  exit 1
fi

# 2. Check GCP Project
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
if [ -z "${PROJECT_ID}" ]; then
  echo "Error: GOOGLE_CLOUD_PROJECT is not set." >&2
  exit 1
fi

REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE_NAME="nerdearla-subtitles-frontend"
BACKEND_SERVICE="nerdearla-subtitles-backend"

# Retrieve Backend URL if not provided
if [ -z "${VITE_API_URL:-}" ]; then
  echo "Detecting backend Cloud Run URL..."
  BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" --region "${REGION}" --project "${PROJECT_ID}" --format="value(status.url)" 2>/dev/null || true)
  if [ -z "${BACKEND_URL}" ]; then
    echo "Warning: Could not auto-detect backend URL. Defaulting to local." >&2
    BACKEND_URL="http://localhost:8080"
  fi
else
  BACKEND_URL="${VITE_API_URL}"
fi

echo "Configuring frontend with Backend URL: ${BACKEND_URL}"

# Build frontend assets locally or via Cloud Build
cd frontend
export VITE_API_URL="${BACKEND_URL}"
npm run build
cd ..

echo "Deploying ${SERVICE_NAME} to Cloud Run in ${REGION}..."
gcloud run deploy "${SERVICE_NAME}" \
  --source ./frontend \
  --region "${REGION}" \
  --platform managed \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 5 \
  --allow-unauthenticated \
  --project "${PROJECT_ID}"

FRONTEND_URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --project "${PROJECT_ID}" --format="value(status.url)")
echo "Frontend deployed at: ${FRONTEND_URL}"
echo "=== Frontend Deployment Complete ==="
