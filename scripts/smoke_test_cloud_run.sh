#!/usr/bin/env bash
set -euo pipefail

# Nerdearla Live Subtitles — Cloud Run Smoke Test Script
# Verifies /health, /ready, /auth/login, and /auth/me against a running deployment.
# Never prints full passwords or JWT tokens to stdout/logs.

BACKEND_URL="${1:-}"
USERNAME="${2:-admin}"
PASSWORD="${3:-}"

if [ -z "${BACKEND_URL}" ]; then
  echo "Usage: $0 <BACKEND_URL> [USERNAME] [PASSWORD]"
  echo "Example: $0 https://nerdearla-subtitles-backend-xyz.run.app admin my-secret-password"
  exit 1
fi

# Trim trailing slash
BACKEND_URL="${BACKEND_URL%/}"

echo "================================================="
echo " Starting Cloud Run Smoke Test: ${BACKEND_URL}"
echo "================================================="

# 1. Test /health
echo -n "Checking /health endpoint... "
HEALTH_RESP=$(curl -fsS "${BACKEND_URL}/health" 2>/dev/null || echo "FAIL")
if [[ "${HEALTH_RESP}" == *"\"status\":\"ok\""* || "${HEALTH_RESP}" == *"\"status\": \"ok\""* ]]; then
  echo "[PASS] /health"
else
  echo "[FAIL] /health response: ${HEALTH_RESP}"
  exit 1
fi

# 2. Test /ready
echo -n "Checking /ready endpoint... "
READY_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/ready" 2>/dev/null || echo "000")
if [ "${READY_HTTP_CODE}" = "200" ]; then
  echo "[PASS] /ready (HTTP 200 - Ready)"
elif [ "${READY_HTTP_CODE}" = "503" ]; then
  echo "[WARN] /ready returned HTTP 503 (Dependencies initializing or Redis offline)"
else
  echo "[FAIL] /ready returned unexpected HTTP ${READY_HTTP_CODE}"
fi

# 3. Test /auth/login
if [ -z "${PASSWORD}" ]; then
  echo ""
  echo "No password supplied. Enter operator password to verify /auth/login and /auth/me:"
  read -s -p "Password: " PASSWORD
  echo ""
fi

echo -n "Checking /auth/login... "
LOGIN_JSON=$(curl -s -X POST "${BACKEND_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}" 2>/dev/null || true)

TOKEN=$(echo "${LOGIN_JSON}" | grep -o '"access_token": *"[^"]*' | sed 's/"access_token": *"//' || true)

if [ -n "${TOKEN}" ]; then
  echo "[PASS] /auth/login (JWT successfully issued)"
else
  echo "[FAIL] /auth/login failed: ${LOGIN_JSON}"
  exit 1
fi

# 4. Test /auth/me
echo -n "Checking /auth/me with Bearer token... "
ME_RESP=$(curl -s -X GET "${BACKEND_URL}/auth/me" \
  -H "Authorization: Bearer ${TOKEN}" 2>/dev/null || true)

if [[ "${ME_RESP}" == *"\"authenticated\":true"* || "${ME_RESP}" == *"\"authenticated\": true"* ]]; then
  echo "[PASS] /auth/me (Identity confirmed)"
else
  echo "[FAIL] /auth/me failed: ${ME_RESP}"
  exit 1
fi

echo "-------------------------------------------------"
echo "[INFO] WebSocket/Gemini test requires browser or dedicated WS client."
echo "================================================="
echo " All HTTP Smoke Tests Completed Successfully!    "
echo "================================================="
