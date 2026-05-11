#!/usr/bin/env python3
"""Merge Zapier OAuth vault entries from a source mcporter credentials.json into a target.

McPorter stores OAuth in ~/.mcporter/credentials.json under keys like ``zapier|<hash>``.
After you finish OAuth on your Mac (where the browser can hit 127.0.0.1), e.g.:

  npx -y -p node@24 -p mcporter mcporter config login zapier \\
      --config /path/to/hermes-agent/config/mcporter.json

merge those entries onto the droplet's file with this script.

Usage:
  python3 scripts/merge_mcporter_zapier_vault.py \\
      --from ~/.mcporter/credentials.json \\
      --into /path/to/droplet/credentials.json \\
      [--write]

  --write updates the --into file in place (default: print merged JSON to stdout).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_vault(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": 1, "entries": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON in {path}: {e}") from e
    if not isinstance(raw, dict):
        raise SystemExit(f"Expected object at top level in {path}")
    if raw.get("version") != 1 or not isinstance(raw.get("entries"), dict):
        # tolerate missing shape by normalizing
        entries = raw.get("entries") if isinstance(raw.get("entries"), dict) else {}
        return {"version": 1, "entries": entries}
    return raw


def merge_zapier_entries(source: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    src_entries = source.get("entries") if isinstance(source.get("entries"), dict) else {}
    tgt_entries = dict(target.get("entries") or {})
    merged = 0
    for k, v in src_entries.items():
        if isinstance(k, str) and k.startswith("zapier|"):
            tgt_entries[k] = v
            merged += 1
    out = {"version": 1, "entries": tgt_entries}
    return out, merged


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from", dest="from_path", type=Path, required=True)
    ap.add_argument("--into", dest="into_path", type=Path, required=True)
    ap.add_argument("--write", action="store_true", help="Overwrite --into with merged result")
    args = ap.parse_args()

    src = load_vault(args.from_path)
    tgt = load_vault(args.into_path)
    out, n = merge_zapier_entries(src, tgt)
    if n == 0:
        raise SystemExit(
            "No keys matching 'zapier|' in source vault. Run on the Mac first, e.g.: "
            "npx -y -p node@24 -p mcporter mcporter config login zapier --reset "
            "--config /path/to/hermes-agent/config/mcporter.json"
        )
    text = json.dumps(out, indent=2, sort_keys=True) + "\n"
    if args.write:
        args.into_path.write_text(text, encoding="utf-8")
        print(f"Merged {n} Zapier vault entr{'y' if n == 1 else 'ies'} into {args.into_path}")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
