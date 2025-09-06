#!/usr/bin/env bash
set -euo pipefail

PYTHON="python3.13"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Installing Python 3.13..."
  sudo apt-get update
  sudo apt-get install -y python3.13 python3.13-venv
fi

# Ensure pip is available and up to date
"$PYTHON" -m ensurepip --upgrade
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt
echo "Create .secrets/kippy.env"
echo "Copy secrets KIPPY_CODEX_EMAIL and KIPPY_CODEX_PASSWORD"
echo "to KIPPY_EMAIL and KIPPY_PASSWORD environment variables."

# Ensure required env vars exist
: "${KIPPY_CODEX_EMAIL?Environment variable KIPPY_CODEX_EMAIL is not set}"
: "${KIPPY_CODEX_PASSWORD?Environment variable KIPPY_CODEX_PASSWORD is not set}"

# Create secrets directory
mkdir -p .secrets

# Write secrets to env file
cat > .secrets/kippy.env <<ENV
KIPPY_EMAIL=${KIPPY_CODEX_EMAIL}
KIPPY_PASSWORD=${KIPPY_CODEX_PASSWORD}
ENV

echo "Wrote credentials to .secrets/kippy.env"
