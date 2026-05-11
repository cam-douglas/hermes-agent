"""Profile-local spend governance for handover v4."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from hermes_constants import get_hermes_home


@dataclass(frozen=True)
class SpendSnapshot:
    period: str
    spent_usd_est: float
    soft_cap_usd: float | None
    hard_cap_usd: float | None

    @property
    def proximity(self) -> float | None:
        cap = self.hard_cap_usd or self.soft_cap_usd
        if not cap:
            return None
        return self.spent_usd_est / float(cap)


def spend_db_path(config: Mapping[str, Any]) -> Path:
    raw = str(config.get("persist_path") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return get_hermes_home() / "state" / "spend.sqlite3"


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS spend_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            session_id TEXT,
            parent_session_id TEXT,
            model TEXT,
            provider TEXT,
            amount_usd REAL NOT NULL
        )
        """
    )
    return conn


def record_spend(
    config: Mapping[str, Any],
    *,
    amount_usd: float,
    session_id: str | None,
    parent_session_id: str | None,
    model: str,
    provider: str,
) -> list[SpendSnapshot]:
    """Persist a spend event and return current turn/day/month snapshots."""
    if not config.get("enabled") or amount_usd <= 0:
        return []

    path = spend_db_path(config)
    now = time.time()
    rollup_session = parent_session_id if config.get("aggregate_delegation", True) and parent_session_id else session_id
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO spend_events
            (ts, session_id, parent_session_id, model, provider, amount_usd)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now, rollup_session, parent_session_id, model, provider, float(amount_usd)),
        )

        soft = config.get("soft_cap") if isinstance(config.get("soft_cap"), dict) else {}
        hard = config.get("hard_cap") if isinstance(config.get("hard_cap"), dict) else {}
        periods = [
            ("turn", _turn_total(conn, rollup_session), soft.get("per_turn_usd"), hard.get("per_turn_usd")),
            ("day", _period_total(conn, "day"), soft.get("per_day_usd"), hard.get("per_day_usd")),
            ("month", _period_total(conn, "month"), soft.get("per_month_usd"), hard.get("per_month_usd")),
        ]
    return [
        SpendSnapshot(p, float(total or 0.0), _to_float(s), _to_float(h))
        for p, total, s, h in periods
    ]


def snapshots_to_payloads(snapshots: list[SpendSnapshot]) -> list[dict[str, Any]]:
    payloads = []
    for snap in snapshots:
        payloads.append({
            "scope": "spend",
            "period": snap.period,
            "spent_usd_est": round(snap.spent_usd_est, 6),
            "soft_cap_usd": snap.soft_cap_usd,
            "hard_cap_usd": snap.hard_cap_usd,
            "proximity": snap.proximity,
        })
    return payloads


def _turn_total(conn: sqlite3.Connection, session_id: str | None) -> float:
    if not session_id:
        return 0.0
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_usd), 0) FROM spend_events WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return float(row[0] or 0.0)


def _period_total(conn: sqlite3.Connection, period: str) -> float:
    now = datetime.now(timezone.utc)
    if period == "day":
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    else:
        start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_usd), 0) FROM spend_events WHERE ts >= ?",
        (start.timestamp(),),
    ).fetchone()
    return float(row[0] or 0.0)


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
