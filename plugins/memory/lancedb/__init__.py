"""LanceDB memory plugin — embedded store (see https://docs.lancedb.com/quickstart).

Stores conversation turns and explicit facts; recalls via vector similarity when
an embedding endpoint is configured, otherwise via lightweight keyword overlap.

Config (env, optional ``$HERMES_HOME/lancedb.json``, or ``memory.lancedb`` in config.yaml):

- ``LANCEDB_URI`` — database directory (default: ``$HERMES_HOME/lancedb_data``)
- ``LANCEDB_EMBEDDING_API_KEY`` — defaults to ``OPENAI_API_KEY``
- ``LANCEDB_EMBEDDING_BASE_URL`` — default ``https://api.openai.com/v1``
- ``LANCEDB_EMBEDDING_MODEL`` — default ``text-embedding-3-small``
- ``LANCEDB_EMBEDDING_DIM`` — vector length (default 1536; must match model)
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from agent.memory_provider import MemoryProvider
from tools.registry import tool_error

logger = logging.getLogger(__name__)

TABLE_NAME = "hermes_memories"
_BOOTSTRAP_ID = "__lancedb_bootstrap__"


def _load_lancedb_config() -> dict:
    from hermes_constants import get_hermes_home

    home = get_hermes_home()
    cfg: Dict[str, Any] = {
        "uri": (os.environ.get("LANCEDB_URI") or "").strip(),
        "embedding_api_key": (
            (os.environ.get("LANCEDB_EMBEDDING_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
        ),
        "embedding_base_url": (
            os.environ.get("LANCEDB_EMBEDDING_BASE_URL") or "https://api.openai.com/v1"
        ).rstrip("/"),
        "embedding_model": (os.environ.get("LANCEDB_EMBEDDING_MODEL") or "text-embedding-3-small").strip(),
        "embedding_dim": int(os.environ.get("LANCEDB_EMBEDDING_DIM") or "1536"),
    }
    path = home / "lancedb.json"
    if path.exists():
        try:
            file_cfg = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(file_cfg, dict):
                for k, v in file_cfg.items():
                    if v is not None and v != "":
                        cfg[k] = v
        except Exception:
            pass
    try:
        cfg["embedding_dim"] = int(cfg.get("embedding_dim", 1536))
    except Exception:
        cfg["embedding_dim"] = 1536
    try:
        from hermes_cli.config import cfg_get, load_config

        yml = load_config() or {}
        uri = cfg_get(yml, "memory", "lancedb", "uri")
        if uri:
            cfg["uri"] = str(uri).strip()
        ek = cfg_get(yml, "memory", "lancedb", "embedding_api_key")
        if ek:
            cfg["embedding_api_key"] = str(ek).strip()
        bu = cfg_get(yml, "memory", "lancedb", "embedding_base_url")
        if bu:
            cfg["embedding_base_url"] = str(bu).rstrip("/")
        em = cfg_get(yml, "memory", "lancedb", "embedding_model")
        if em:
            cfg["embedding_model"] = str(em).strip()
        dim = cfg_get(yml, "memory", "lancedb", "embedding_dim")
        if dim is not None:
            cfg["embedding_dim"] = int(dim)
    except Exception:
        pass

    if not cfg["uri"]:
        cfg["uri"] = str(home / "lancedb_data")
    try:
        cfg["embedding_dim"] = int(cfg.get("embedding_dim", 1536))
    except Exception:
        cfg["embedding_dim"] = 1536
    return cfg


def _sanitize_sql_string(s: str) -> str:
    return (s or "").replace("'", "''")


def _tokenize(text: str) -> set[str]:
    return {t for t in re.split(r"\W+", (text or "").lower()) if len(t) > 1}


def _keyword_score(query: str, doc: str) -> float:
    q, d = _tokenize(query), _tokenize(doc)
    if not q or not d:
        return 0.0
    return float(len(q & d)) / float(len(q))


PROFILE_SCHEMA = {
    "name": "lancedb_profile",
    "description": (
        "List stored LanceDB memories for this user (full dump, no ranking). "
        "Use for a broad overview; prefer lancedb_search for targeted recall."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}

SEARCH_SCHEMA = {
    "name": "lancedb_search",
    "description": "Semantic or keyword search over LanceDB memories.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for."},
            "top_k": {"type": "integer", "description": "Max hits (default 8, max 50)."},
        },
        "required": ["query"],
    },
}

REMEMBER_SCHEMA = {
    "name": "lancedb_remember",
    "description": "Store an explicit durable fact in LanceDB (verbatim text).",
    "parameters": {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Fact or note to remember."}},
        "required": ["text"],
    },
}


class LanceDBMemoryProvider(MemoryProvider):
    @property
    def name(self) -> str:
        return "lancedb"

    def __init__(self) -> None:
        self._cfg: dict = {}
        self._user_id = "hermes-user"
        self._profile = ""
        self._session_id = ""
        self._db = None
        self._table = None
        self._dim = 1536
        self._db_lock = threading.Lock()
        self._prefetch_result = ""
        self._prefetch_lock = threading.Lock()
        self._prefetch_thread: Optional[threading.Thread] = None
        self._sync_thread: Optional[threading.Thread] = None
        self._vectors_effective = False

    def is_available(self) -> bool:
        try:
            import lancedb  # noqa: F401
        except ImportError:
            return False
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        self._cfg = _load_lancedb_config()
        self._dim = int(self._cfg.get("embedding_dim") or 1536)
        self._session_id = session_id or ""
        self._user_id = str(kwargs.get("user_id") or "hermes-user")
        self._profile = str(kwargs.get("agent_identity") or "")
        self._vectors_effective = bool(self._cfg.get("embedding_api_key"))
        self._ensure_table()

    def _ensure_table(self) -> None:
        import lancedb

        uri = str(self._cfg.get("uri") or "")
        Path = __import__("pathlib").Path
        Path(uri).mkdir(parents=True, exist_ok=True)

        with self._db_lock:
            self._db = lancedb.connect(uri)
            listed = self._db.list_tables()
            names = list(getattr(listed, "tables", ()) or ())
            if TABLE_NAME in names:
                self._table = self._db.open_table(TABLE_NAME)
                return
            bootstrap = [{
                "id": _BOOTSTRAP_ID,
                "text": "",
                "session_id": "",
                "user_id": "",
                "profile": "",
                "created": 0.0,
                "vector": [0.0] * self._dim,
            }]
            self._table = self._db.create_table(TABLE_NAME, data=bootstrap, mode="overwrite")

    def _open_table(self):
        with self._db_lock:
            if self._table is not None:
                return self._table
        self._ensure_table()
        return self._table

    def _embed(self, text: str) -> Optional[List[float]]:
        key = self._cfg.get("embedding_api_key") or ""
        if not key or not (text or "").strip():
            return None
        try:
            import httpx
            from hermes_cli.models import _HERMES_USER_AGENT

            url = f"{self._cfg['embedding_base_url']}/embeddings"
            payload = {"model": self._cfg["embedding_model"], "input": (text or "")[:8000]}
            r = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "User-Agent": _HERMES_USER_AGENT,
                },
                json=payload,
                timeout=60.0,
            )
            if r.status_code != 200:
                logger.debug("LanceDB embed HTTP %s: %s", r.status_code, r.text[:200])
                return None
            data = r.json()
            vec = (data.get("data") or [{}])[0].get("embedding")
            if not isinstance(vec, list):
                return None
            if len(vec) != self._dim:
                logger.warning(
                    "LanceDB embedding dim mismatch: got %s expected %s — adjust LANCEDB_EMBEDDING_DIM",
                    len(vec),
                    self._dim,
                )
                return None
            return [float(x) for x in vec]
        except Exception as e:
            logger.debug("LanceDB embed failed: %s", e)
            return None

    def _append_row(self, text: str, session_id: str, source: str = "turn") -> None:
        if not (text or "").strip():
            return
        tid = self._open_table()
        vec = self._embed(text)
        if vec is None:
            vec = [0.0] * self._dim
        row = {
            "id": str(uuid.uuid4()),
            "text": text.strip(),
            "session_id": session_id or self._session_id,
            "user_id": self._user_id,
            "profile": self._profile,
            "created": time.time(),
            "vector": vec,
        }
        try:
            tid.add([row])
        except Exception as e:
            logger.warning("LanceDB add failed: %s", e)

    def system_prompt_block(self) -> str:
        return (
            "# LanceDB Memory\n"
            f"Active. Local DB: {self._cfg.get('uri', '?')}. User: {self._user_id}.\n"
            "Use lancedb_search for recall, lancedb_remember to store facts, "
            "lancedb_profile for a full list."
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        if self._prefetch_thread and self._prefetch_thread.is_alive():
            self._prefetch_thread.join(timeout=3.0)
        with self._prefetch_lock:
            result = self._prefetch_result
            self._prefetch_result = ""
        if not result:
            return ""
        return f"## LanceDB Memory\n{result}"

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        if not (query or "").strip():
            return

        def _run():
            try:
                lines = self._search_impl(query, top_k=5)
                if lines:
                    with self._prefetch_lock:
                        self._prefetch_result = "\n".join(f"- {t}" for t, _s in lines)
            except Exception as e:
                logger.debug("LanceDB prefetch failed: %s", e)

        self._prefetch_thread = threading.Thread(target=_run, daemon=True, name="lancedb-prefetch")
        self._prefetch_thread.start()

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        if not (user_content or "").strip() and not (assistant_content or "").strip():
            return
        blob = f"User:\n{user_content}\n\nAssistant:\n{assistant_content}".strip()
        if len(blob) < 12:
            return

        sid = session_id or self._session_id

        def _sync():
            self._append_row(blob, sid, source="turn")

        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=8.0)
        self._sync_thread = threading.Thread(target=_sync, daemon=True, name="lancedb-sync")
        self._sync_thread.start()

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [PROFILE_SCHEMA, SEARCH_SCHEMA, REMEMBER_SCHEMA]

    def _search_impl(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        tid = self._open_table()
        uid = _sanitize_sql_string(self._user_id)
        # Exclude bootstrap / empty rows
        base_where = f"(user_id = '{uid}') AND (id != '{_BOOTSTRAP_ID}') AND (text != '')"

        if self._vectors_effective:
            qvec = self._embed(query)
            if qvec is not None:
                try:
                    hits = tid.search(qvec).where(base_where).limit(top_k).to_arrow()
                    out: List[Tuple[str, float]] = []
                    if hits is not None and hits.num_rows > 0:
                        text_col = hits.column("text")
                        names = hits.schema.names
                        dist_col = hits.column("_distance") if "_distance" in names else None
                        for i in range(hits.num_rows):
                            txt = str(text_col[i].as_py() or "")
                            dist = float(dist_col[i].as_py()) if dist_col is not None else 0.0
                            out.append((txt, dist))
                    if out:
                        return out
                except Exception as e:
                    logger.debug("LanceDB vector search failed, falling back: %s", e)

        # Keyword fallback (pyarrow scan — no pandas dependency)
        try:
            arrow_tbl = tid.to_arrow()
        except Exception as e:
            logger.warning("LanceDB to_arrow failed: %s", e)
            return []
        if arrow_tbl is None or arrow_tbl.num_rows == 0:
            return []
        scored_rows: List[Tuple[str, float, float]] = []
        cols = {arrow_tbl.schema.field(j).name: arrow_tbl.column(j) for j in range(arrow_tbl.num_columns)}
        id_c = cols.get("id")
        uid_c = cols.get("user_id")
        text_c = cols.get("text")
        created_c = cols.get("created")
        if id_c is None or uid_c is None or text_c is None:
            return []
        for i in range(arrow_tbl.num_rows):
            rid = id_c[i].as_py()
            if rid == _BOOTSTRAP_ID:
                continue
            if uid_c[i].as_py() != self._user_id:
                continue
            t = text_c[i].as_py()
            if not t:
                continue
            ts = float(created_c[i].as_py()) if created_c is not None else 0.0
            scored_rows.append((str(t), _keyword_score(query, str(t)), ts))
        scored_rows.sort(key=lambda x: x[1], reverse=True)
        top_scored = [(t, s) for t, s, _cr in scored_rows[:top_k] if s > 0]
        if top_scored:
            return top_scored
        return [(t, s) for t, s, _cr in scored_rows[:top_k]]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        if tool_name == "lancedb_profile":
            try:
                tid = self._open_table()
                arrow_tbl = tid.to_arrow()
                if arrow_tbl is None or arrow_tbl.num_rows == 0:
                    return json.dumps({"result": "No memories stored yet."})
                cols = {arrow_tbl.schema.field(j).name: arrow_tbl.column(j) for j in range(arrow_tbl.num_columns)}
                id_c, uid_c, text_c, created_c = cols.get("id"), cols.get("user_id"), cols.get("text"), cols.get("created")
                if id_c is None or uid_c is None or text_c is None:
                    return json.dumps({"result": "No memories stored yet."})
                buf: List[Tuple[float, str]] = []
                for i in range(arrow_tbl.num_rows):
                    if id_c[i].as_py() == _BOOTSTRAP_ID:
                        continue
                    if uid_c[i].as_py() != self._user_id:
                        continue
                    tx = text_c[i].as_py()
                    if not tx:
                        continue
                    cr = float(created_c[i].as_py()) if created_c is not None else 0.0
                    buf.append((cr, str(tx)))
                if not buf:
                    return json.dumps({"result": "No memories stored yet."})
                buf.sort(key=lambda x: x[0], reverse=True)
                lines = [t for _c, t in buf]
                return json.dumps({"result": "\n".join(lines), "count": len(lines)})
            except Exception as e:
                return tool_error(f"Profile failed: {e}")

        if tool_name == "lancedb_search":
            q = str(args.get("query") or "").strip()
            if not q:
                return tool_error("Missing required parameter: query")
            top_k = min(max(int(args.get("top_k", 8)), 1), 50)
            try:
                rows = self._search_impl(q, top_k=top_k)
                if not rows:
                    return json.dumps({"results": [], "message": "No relevant memories found."})
                items = [{"text": t, "score": round(s, 6)} for t, s in rows if t]
                return json.dumps({"results": items, "count": len(items)})
            except Exception as e:
                return tool_error(f"Search failed: {e}")

        if tool_name == "lancedb_remember":
            text = str(args.get("text") or "").strip()
            if not text:
                return tool_error("Missing required parameter: text")
            try:
                self._append_row(text, self._session_id, source="explicit")
                return json.dumps({"result": "Stored in LanceDB."})
            except Exception as e:
                return tool_error(f"Store failed: {e}")

        return tool_error(f"Unknown tool: {tool_name}")

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        **kwargs,
    ) -> None:
        if new_session_id:
            self._session_id = new_session_id

    def shutdown(self) -> None:
        for t in (self._prefetch_thread, self._sync_thread):
            if t and t.is_alive():
                t.join(timeout=5.0)
        with self._db_lock:
            self._table = None
            self._db = None


def register(ctx) -> None:
    ctx.register_memory_provider(LanceDBMemoryProvider())
