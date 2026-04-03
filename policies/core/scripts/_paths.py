"""Shared paths for policy pipeline scripts (repository root + policies root)."""
from __future__ import annotations

from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
# policies/core/scripts -> policies/
POLICIES_ROOT = SCRIPTS_DIR.parent.parent
REPO_ROOT = POLICIES_ROOT.parent
STATE_DIR = POLICIES_ROOT / ".pipeline_state"
MANIFEST_PATH = STATE_DIR / "manifest.json"
