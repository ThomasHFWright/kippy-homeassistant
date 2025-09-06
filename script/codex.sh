pip install -r requirements.txt
echo "Create .secrets/kippy.env"
echo "Copy secrets KIPPY_CODEX_EMAIL and KIPPY_CODEX_PASSWORD"
echo "to KIPPY_EMAIL and KIPPY_PASSWORD environment variables."
set -euo pipefail

# Ensure required env vars exist
: "${KIPPY_CODEX_EMAIL?Environment variable KIPPY_EMAIL is not set}"
: "${KIPPY_CODEX_PASSWORD?Environment variable KIPPY_PASSWORD is not set}"

# Create secrets directory
mkdir -p .secrets

# Write secrets to env file
cat > .secrets/kippy.env <<ENV
KIPPY_EMAIL=${KIPPY_CODEX_EMAIL}
KIPPY_PASSWORD=${KIPPY_CODEX_PASSWORD}
ENV

echo "Wrote credentials to .secrets/kippy.env"