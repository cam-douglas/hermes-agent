"""End-to-end tests for the agentic company policy pipeline scripts.

Runs real scripts against the repository tree. Strict-cue failure is tested in one
block to avoid parallel test races on policies/core/governance/standards/*.md.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_BAD_CORE = REPO / "policies/core/governance/standards/_test_bad_policy_for_pipeline.md"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


def test_pipeline_verify_generate_and_start_sequential() -> None:
    """Verify → index → start full pipeline; strict cue failure; restore."""
    assert _run(["policies/core/scripts/verify_policy_tree.py"]).returncode == 0
    assert _run(["policies/core/scripts/generate_index.py"]).returncode == 0
    dr = _run(["policies/core/scripts/start_pipeline.py", "--dry-run"])
    assert dr.returncode == 0, dr.stderr + dr.stdout
    assert "DRY-RUN verify OK" in dr.stdout

    full = _run(["policies/core/scripts/start_pipeline.py"])
    assert full.returncode == 0, full.stderr + full.stdout

    try:
        _BAD_CORE.write_text("# Only a title\n\nNo activation section.\n", encoding="utf-8")
        bad = _run(["policies/core/scripts/verify_policy_tree.py"])
        assert bad.returncode == 1
        assert "activation" in (bad.stderr + bad.stdout).lower()
    finally:
        if _BAD_CORE.exists():
            _BAD_CORE.unlink()

    assert _run(["policies/core/scripts/verify_policy_tree.py"]).returncode == 0


def test_activation_marker_strings() -> None:
    text_ok = "## Activation prompt (role reminder)\n\n- cue\n"
    text_bad = "# Title\n\nbody only\n"
    markers = (
        "## Activation prompt (role reminder)",
        "## Activation prompt",
    )
    assert any(m in text_ok for m in markers)
    assert not any(m in text_bad for m in markers)
