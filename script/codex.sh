pip install -r requirements.txt
echo "Create .secrets/kippy.env with KIPPY_EMAIL and KIPPY_PASSWORD"
echo "used for local development. Expects KIPPY_EMAIL and KIPPY_PASSWORD"
echo "to be set in the environment."
set -euo pipefail

# Ensure required env vars exist
: "${KIPPY_EMAIL?Environment variable KIPPY_EMAIL is not set}"
: "${KIPPY_PASSWORD?Environment variable KIPPY_PASSWORD is not set}"

# Create secrets directory
mkdir -p .secrets

# Write secrets to env file
cat > .secrets/kippy.env <<ENV
KIPPY_EMAIL=${KIPPY_CODEX_EMAIL}
KIPPY_PASSWORD=${KIPPY_CODEX_PASSWORD}
ENV

echo "Wrote credentials to .secrets/kippy.env"