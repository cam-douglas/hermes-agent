#!/usr/bin/env bash
# Copy repo .env → ~/.hermes/.env, dropping droplet-only API keys and *_LOCAL aliases.
# Run from repo root: ./scripts/sync_hermes_home_env.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/.env"
DST="${HERMES_HOME:-${HOME}/.hermes}/.env"
if [[ ! -f "${SRC}" ]]; then
  echo "Missing ${SRC}" >&2
  exit 1
fi
awk '
  /^OPENAI_API_KEY_DROPLET=/ { next }
  /^ANTHROPIC_API_KEY_DROPLET=/ { next }
  /^GROK_API_KEY_DROPLET=/ { next }
  /^GEMINI_API_KEY_DROPLET=/ { next }
  /^HUGGINGFACE_API_KEY_DROPLET=/ { next }
  /^OPENROUTER_API_KEY_DROPLET=/ { next }
  /^OPENAI_API_KEY_LOCAL=/ { next }
  /^ANTHROPIC_API_KEY_LOCAL=/ { next }
  /^GROK_API_KEY_LOCAL=/ { next }
  /^GEMINI_API_KEY_LOCAL=/ { next }
  /^HUGGINGFACE_API_KEY_LOCAL=/ { next }
  /^OPENROUTER_API_KEY_LOCAL=/ { next }
  { print }
' "${SRC}" > "${DST}.tmp"
mv "${DST}.tmp" "${DST}"
echo "Wrote ${DST}"
