#!/usr/bin/env bash
# Global entry point for the agentic company policy pipeline (repository root).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/policies/core/scripts/start_pipeline.py" "$@"
