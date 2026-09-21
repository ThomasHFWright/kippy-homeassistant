#!/usr/bin/env bash
# Use the standard setup path; never modify the global TLS configuration.
set -euo pipefail
exec "$(dirname "$0")/setup" "$@"
