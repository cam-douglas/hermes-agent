#!/usr/bin/env python3
"""
Global entry point for the agentic company policy pipeline.

From repository root:
  python policies/core/scripts/start_pipeline.py
  python policies/core/scripts/start_pipeline.py --dry-run   # verify only, no writes
  python policies/core/scripts/start_pipeline.py --init-operations  # also create operations stubs if missing
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from _paths import REPO_ROOT
import pipeline_manifest
import verify_policy_tree
from generate_index import run_generate_index
import apply_read_order_navigation


def _run_init_operations_stubs() -> int:
    script = _SCRIPT_DIR / "init_operations_stubs.py"
    r = subprocess.run([sys.executable, str(script)], cwd=REPO_ROOT, check=False)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Agentic company policy pipeline: verify tree, strict activation cues, refresh INDEX, update manifest.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Run verification only; print manifest diff; do not write INDEX.md or manifest (use before deploy to validate).",
    )
    ap.add_argument(
        "--init-operations",
        action="store_true",
        help="After success, run init_operations_stubs.py (creates missing operations/*.md only).",
    )
    ap.add_argument(
        "--no-strict",
        action="store_true",
        help="Skip activation-cue checks on policies/core/governance/standards/*.md (not recommended for deployment).",
    )
    args = ap.parse_args()
    strict = not args.no_strict

    current = pipeline_manifest.compute_manifest()
    saved = pipeline_manifest.load_saved_manifest()

    if args.dry_run:
        code, errs = verify_policy_tree.verify_tree(strict_activation=strict)
        if code != 0:
            print("start_pipeline: DRY-RUN FAILED", file=sys.stderr)
            for e in errs:
                print(" ", e, file=sys.stderr)
            return 1
        print("start_pipeline: DRY-RUN verify OK (strict activation cues)" if strict else "start_pipeline: DRY-RUN verify OK (non-strict)")
        print(" Manifest diff vs last successful run:")
        for line in pipeline_manifest.diff_manifest(current, saved):
            print(" ", line)
        print(f" Tracked: {pipeline_manifest.describe_manifest()}")
        print("start_pipeline: DRY-RUN — no files written")
        return 0

    code, errs = verify_policy_tree.verify_tree(strict_activation=strict)
    if code != 0:
        print("start_pipeline: FAILED (verification)", file=sys.stderr)
        for e in errs:
            print(" ", e, file=sys.stderr)
        return 1

    changed = pipeline_manifest.manifest_changed(current, saved)
    if changed:
        print("start_pipeline: tracked policy files changed since last run — refreshing INDEX and manifest")
        for line in pipeline_manifest.diff_manifest(current, saved):
            print(" ", line)
    else:
        print("start_pipeline: no file changes since last run — refreshing INDEX and manifest (idempotent)")

    gcode, gmsg = run_generate_index()
    if gcode != 0:
        print(f"start_pipeline: INDEX generation failed: {gmsg}", file=sys.stderr)
        return 1
    print(gmsg)

    nav_code = apply_read_order_navigation.main()
    if nav_code != 0:
        print("start_pipeline: read-order navigation refresh failed", file=sys.stderr)
        return 1

    if args.init_operations:
        ic = _run_init_operations_stubs()
        if ic != 0:
            print("start_pipeline: init_operations_stubs failed", file=sys.stderr)
            return 1

    pipeline_manifest.write_manifest(current)
    print("start_pipeline: COMPLETE — verification passed; INDEX and manifest updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
