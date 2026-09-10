#!/usr/bin/env bash
# Serve this directory over HTTP. Default port 8951.
#   ./serve.sh            # foreground
#   nohup ./serve.sh &    # background
# Public exposure is via the cloudflared tunnel on mbp1 (see README.md).
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-8951}"
PY=$(command -v python3 || command -v python)
exec "$PY" -m http.server "$PORT" --bind 0.0.0.0
