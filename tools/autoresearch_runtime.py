"""Autoresearch ``program.md`` outer wall-clock runtime for the agent loop.

The autoresearch workflow stores experiment briefs in ``program.md`` under the
repo-autoresearch skill checkout. When present, Hermes raises the iteration cap
and stops the tool loop when the outer wall-clock budget is reached, matching
``docs/hermes-autoresearch-one-step.md``.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

AUTORESEARCH_WALLCLOCK_STATE_FILENAME = "autoresearch_wallclock_state.json"

# Must appear near the top of ``program.md`` for the file to be treated as autoresearch.
_AUTORESEARCH_MARKERS = (
    "# autoresearch",
    "# Autoresearch",
)


def _get_hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home

        return Path(get_hermes_home())
    except Exception:
        return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def resolve_autoresearch_program_path() -> Optional[Path]:
    """Return path to ``program.md`` if it exists."""
    env = (os.environ.get("HERMES_AUTORESEARCH_PROGRAM") or "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p.resolve()
        logger.debug("HERMES_AUTORESEARCH_PROGRAM set but not a file: %s", env)
        return None
    candidate = (
        _get_hermes_home()
        / "skills/software-development/repo-autoresearch-cpu/checkout/program.md"
    )
    if candidate.is_file():
        return candidate.resolve()
    return None


def resolve_autoresearch_checkout_dir() -> Path:
    """Directory containing ``training`` entrypoints (parent of ``program.md``).

    If ``program.md`` is not on disk yet, returns the canonical checkout path
    under :func:`_get_hermes_home` so operators still get a valid ``cd``.
    """
    p = resolve_autoresearch_program_path()
    if p is not None:
        return p.parent
    return (
        _get_hermes_home()
        / "skills/software-development/repo-autoresearch-cpu/checkout"
    ).resolve()


def format_autoresearch_train_commands(
    *,
    checkout_dir: Path,
    budget_minutes: int,
) -> Dict[str, str]:
    """Shell one-liners for a **second terminal** (training subprocess).

    **Preferred** line uses ``python3`` or a ``checkout/.venv`` (``venv``) interpreter
    so hosts without ``uv`` avoid exit 127. An optional ``uv run`` line is included
    when ``uv`` is on ``PATH``.
    """
    import shutil
    import shlex

    minutes = max(1, int(budget_minutes))
    seconds = minutes * 60
    cd = shlex.quote(str(checkout_dir.resolve()))
    env = f"HERMES_AUTORESEARCH_OUTER_MINUTES={minutes} "

    py = "python3"
    for candidate in (
        checkout_dir / ".venv" / "bin" / "python",
        checkout_dir / "venv" / "bin" / "python",
    ):
        try:
            if candidate.is_file():
                py = str(candidate.resolve())
                break
        except OSError:
            continue
    py_token = shlex.quote(py) if py != "python3" else "python3"

    train_py = f"cd {cd} && {env}timeout {seconds} {py_token} train.py"
    train_uv = ""
    if shutil.which("uv"):
        train_uv = f"cd {cd} && {env}timeout {seconds} uv run train.py"

    prepare_py = f"cd {cd} && {py_token} prepare.py --num-shards 4"
    prepare_uv = ""
    if shutil.which("uv"):
        prepare_uv = f"cd {cd} && uv run prepare.py --num-shards 4"

    result = {
        "train_recommended_cmd": train_py,
        "prepare_recommended_cmd": prepare_py,
    }
    if train_uv:
        result["train_uv_cmd"] = train_uv
    if prepare_uv:
        result["prepare_uv_cmd"] = prepare_uv
    return result


def _wallclock_state_payload(
    *,
    session_id: str,
    deadline_epoch: float,
    budget_minutes: int,
    provenance: str,
) -> Dict[str, Any]:
    import shlex

    sid = session_id or ""
    sid_token = shlex.quote(sid) if sid else '""'
    root = _get_hermes_home()
    state_path = root / AUTORESEARCH_WALLCLOCK_STATE_FILENAME
    checkout = resolve_autoresearch_checkout_dir()
    train_cmds = format_autoresearch_train_commands(
        checkout_dir=checkout,
        budget_minutes=budget_minutes,
    )
    payload: Dict[str, Any] = {
        "session_id": sid,
        "deadline_epoch": deadline_epoch,
        "budget_minutes": budget_minutes,
        "provenance": provenance,
        "follow_logs_cmd": f"hermes logs -f --session {sid_token}",
        "attach_chat_cmd": f"hermes chat --continue {sid_token}",
        "checkout_dir": str(checkout),
        "state_file": str(state_path.resolve()),
        **train_cmds,
    }
    return payload


def _is_autoresearch_program(text: str) -> bool:
    head = "\n".join(text.splitlines()[:120])
    return any(m in head for m in _AUTORESEARCH_MARKERS)


def parse_outer_runtime_minutes(text: str) -> Optional[int]:
    """Parse explicit outer runtime in minutes from program body.

    Looks for phrases like ``120 minutes``, ``outer runtime ... 45 min``, etc.
    Returns None if no explicit duration found (caller may apply default).
    """
    # Phrases near "outer" / "runtime" / "total" / "wall"
    patterns = [
        r"(?i)outer\s+runtime[^\n]{0,120}?(\d{1,6})\s*(?:minutes?|mins?)\b",
        r"(?i)total\s+outer[^\n]{0,120}?(\d{1,6})\s*(?:minutes?|mins?)\b",
        r"(?i)wall(?:-|\s+)clock[^\n]{0,120}?(\d{1,6})\s*(?:minutes?|mins?)\b",
        r"(?i)\b(\d{1,6})\s*(?:minutes?|mins?)\s+total\b",
        r"(?i)run\s+for\s+(\d{1,6})\s*(?:minutes?|mins?)\b",
        r"(?i)\b(\d{1,6})\s*(?:minutes?|mins?)\s+(?:for\s+)?(?:the\s+)?(?:full\s+)?(?:experiment|session|loop)\b",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            try:
                n = int(m.group(1))
                if 1 <= n <= 1_000_000:
                    return n
            except (TypeError, ValueError):
                continue
    return None


def load_autoresearch_outer_runtime_minutes() -> Optional[Tuple[int, str]]:
    """Load (minutes, provenance) when an autoresearch program is active.

    Precedence:
    1. ``HERMES_AUTORESEARCH_OUTER_MINUTES`` environment variable.
    2. Parsed duration from ``program.md``; if autoresearch program but no
       explicit duration, **600** minutes (handbook default).
    """
    raw = (os.environ.get("HERMES_AUTORESEARCH_OUTER_MINUTES") or "").strip()
    if raw:
        try:
            n = int(raw)
            if 1 <= n <= 1_000_000:
                return (n, "env:HERMES_AUTORESEARCH_OUTER_MINUTES")
        except ValueError:
            logger.warning("Invalid HERMES_AUTORESEARCH_OUTER_MINUTES=%r", raw)

    path = resolve_autoresearch_program_path()
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Could not read autoresearch program %s: %s", path, exc)
        return None
    if not _is_autoresearch_program(text):
        return None
    explicit = parse_outer_runtime_minutes(text)
    minutes = explicit if explicit is not None else 600
    return (minutes, str(path))


def persist_autoresearch_wallclock_state(
    *,
    session_id: str,
    deadline_epoch: float,
    budget_minutes: int,
    provenance: str,
) -> None:
    """Write JSON state for operators (second terminal, scripts, dashboards)."""
    try:
        root = _get_hermes_home()
        root.mkdir(parents=True, exist_ok=True)
        state_path = root / AUTORESEARCH_WALLCLOCK_STATE_FILENAME
        payload = _wallclock_state_payload(
            session_id=session_id,
            deadline_epoch=deadline_epoch,
            budget_minutes=budget_minutes,
            provenance=provenance,
        )
        state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.debug("Could not persist autoresearch wall-clock state: %s", exc)


def clear_autoresearch_wallclock_state() -> None:
    """Remove persisted wall-clock state when autoresearch is not active."""
    try:
        p = _get_hermes_home() / AUTORESEARCH_WALLCLOCK_STATE_FILENAME
        if p.is_file():
            p.unlink()
    except OSError:
        pass
