#!/usr/bin/env python3
"""Create policies/core/governance/generated/by_role/<slug>/ from _TEMPLATE (standards, playbooks, decisions, scratch)."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parents[1]
TEMPLATE = CORE / "governance" / "generated" / "by_role" / "_TEMPLATE"


def main() -> int:
    ap = argparse.ArgumentParser(description="Materialize a role workspace under policies/core/governance/generated/by_role/")
    ap.add_argument("slug", help="folder name, e.g. product_lead")
    ap.add_argument("--title", default="", help="human-readable role title (optional)")
    args = ap.parse_args()
    slug = args.slug.strip().replace(" ", "_")
    if not slug or ".." in slug:
        print("invalid slug", file=sys.stderr)
        return 1
    dest = CORE / "governance" / "generated" / "by_role" / slug
    if dest.exists():
        print(f"already exists: {dest}", file=sys.stderr)
        return 1
    shutil.copytree(TEMPLATE, dest)
    readme = dest / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = text.replace("<role_slug>", slug)
    if args.title:
        text = text.replace("_[human-readable role title]_", args.title)
    readme.write_text(text, encoding="utf-8")
    for sub in ("standards", "playbooks", "decisions", "scratch"):
        (dest / sub).mkdir(exist_ok=True)
        (dest / sub / ".gitkeep").write_text("", encoding="utf-8")
    print(f"Created {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
