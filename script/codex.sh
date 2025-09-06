#!/usr/bin/env bash
set -euo pipefail

PY_VERSION="3.13.3"
if ! pyenv versions --bare | grep -qx "$PY_VERSION"; then
  echo "Installing Python $PY_VERSION via pyenv..."
  pyenv install "$PY_VERSION"
fi

pyenv local "$PY_VERSION"
PYTHON="python"

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
