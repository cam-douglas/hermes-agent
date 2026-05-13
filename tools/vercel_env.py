"""Resolve Vercel Sandbox credentials from link files and optional fallbacks.

The Vercel Python SDK requires ``VERCEL_TOKEN``, ``VERCEL_PROJECT_ID``, and
``VERCEL_TEAM_ID`` together (unless ``VERCEL_OIDC_TOKEN`` is used). Sandbox
runs are always scoped to a single Vercel *project*; creating or editing
*other* projects still uses the same token with the Vercel API / CLI and does
not remove the need for a Sandbox host project.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

__all__ = [
    "read_nearest_vercel_project_json",
    "ensure_vercel_project_id_for_sandbox",
]


def read_nearest_vercel_project_json(start: Path | None = None) -> dict[str, str]:
    """Return ``projectId`` / ``orgId`` from the nearest ``.vercel/project.json`` upward."""
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for directory in (current, *current.parents):
        project_file = directory / ".vercel" / "project.json"
        if not project_file.is_file():
            continue
        try:
            data = json.loads(project_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            key: value
            for key, value in {
                "projectId": data.get("projectId"),
                "orgId": data.get("orgId"),
            }.items()
            if isinstance(value, str) and value.strip()
        }
    return {}


def _link_search_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            roots.append(path.resolve())

    add(Path.cwd())
    for raw in os.getenv("VERCEL_LINK_SEARCH_PATHS", "").split(os.pathsep):
        part = raw.strip()
        if part:
            add(Path(part).expanduser())

    return roots


def ensure_vercel_project_id_for_sandbox() -> str | None:
    """Set ``VERCEL_PROJECT_ID`` (and optionally ``VERCEL_TEAM_ID``) when inferable.

    Order: existing ``VERCEL_PROJECT_ID`` → nearest ``.vercel/project.json`` for
    each search root → ``VERCEL_DEFAULT_PROJECT_ID``.

    Returns the effective project id, or ``None`` if still unset.
    """
    if os.getenv("VERCEL_OIDC_TOKEN"):
        return (os.getenv("VERCEL_PROJECT_ID") or "").strip() or None

    existing = (os.getenv("VERCEL_PROJECT_ID") or "").strip()
    if existing:
        return existing

    for root in _link_search_roots():
        linked = read_nearest_vercel_project_json(root)
        project_id = linked.get("projectId", "").strip()
        if project_id:
            os.environ["VERCEL_PROJECT_ID"] = project_id
            org = linked.get("orgId", "").strip()
            if org and not (os.getenv("VERCEL_TEAM_ID") or "").strip():
                os.environ["VERCEL_TEAM_ID"] = org
            return project_id

    fallback = (os.getenv("VERCEL_DEFAULT_PROJECT_ID") or "").strip()
    if fallback:
        os.environ["VERCEL_PROJECT_ID"] = fallback
        return fallback

    return None
