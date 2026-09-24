#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

cd "${ROOT_DIR}"

echo "================================================="
echo " Starting Full Deployment: Nerdearla Subtitles  "
echo "================================================="

# Step 1: Deploy Backend
bash "${SCRIPT_DIR}/backend.sh"

# Step 2: Deploy Frontend
bash "${SCRIPT_DIR}/frontend.sh"

echo "================================================="
echo " Full Deployment Completed Successfully!         "
echo "================================================="
