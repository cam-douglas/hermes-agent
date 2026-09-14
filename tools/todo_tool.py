"""Todo tool: in-memory, revisioned task list for multi-step work. State lives on the
AIAgent (one per session), is re-injected after context compression, and every write bumps
a monotonic revision so UI clients can reject stale updates. One ``todo_list`` tool: pass
``todos`` to write, omit to read; every call returns the full list. No system-prompt mutation.

Cam (the user) owns completion. The agent may create, edit, and advance items to
``in_progress``, but ``completed`` only sticks after the user confirms (chat
``done`` / ``complete``, or the Desktop task list)."""

import json
import re
from typing import Any, Dict, List, Optional

VALID_STATUSES = {"pending", "in_progress", "completed", "cancelled"}
# The list is re-read after every compression (format_for_injection), so unbounded
# content/count would defeat the compression it rides through. Caps apply equally to
# model-authored items and caller-replayed API history.
MAX_TODO_CONTENT_CHARS = 4000
MAX_TODO_ITEMS = 256
# Max single todo tool-result payload accepted during history hydration, so a forged
# oversized result is dropped before parsing (AIAgent._hydrate_todo_store).
MAX_TODO_RESULT_CHARS = 512_000
_TRUNCATION_MARKER = "… [truncated]"
# Persisted as ordinary message content; ContextCompressor keys on this stable header to
# tell the synthetic post-compaction row from a real user message.
TODO_INJECTION_HEADER = "[Your active task list was preserved across context compression]"
_STATUS_MARKERS = {"completed": "[x]", "in_progress": "[>]", "pending": "[ ]", "cancelled": "[~]"}
_ACTIVE_STATUSES = {"pending", "in_progress"}


# Whole-message user confirmation. "please complete the login page" does not match.
_CONFIRM_ALL = re.compile(
    r"^\s*(?:(?:ok(?:ay)?|yes|yeah|yep)[,.]?\s+)?"
    r"(?:(?:that['’]?s|it['’]?s|its)\s+)?"
    r"(?:all\s+|everything\s+(?:is\s+)?)?"
    r"(?:done|complete|completed|finished)\s*[.!]?\s*$",
    re.I,
)
_MARK_DONE = re.compile(
    r"\bmark\s+(.+?)\s+(?:as\s+)?(?:done|complete|completed|finished)\b",
    re.I,
)
_TASK_ID_DONE = re.compile(
    r"\b(?:task|item|todo)\s+#?([A-Za-z0-9._-]+)\s+(?:is\s+)?(?:done|complete|completed|finished)\b",
    re.I,
)
_NUM_DONE = re.compile(
    r"(?:^|[^\w])#?(\d+)\s+(?:is\s+)?(?:done|complete|completed|finished)\b",
    re.I,
)
_BARE_DONE = frozenset({
    "done", "complete", "completed", "finished",
    "that's done", "thats done", "that's complete", "thats complete",
    "it's done", "its done", "it's complete", "its complete",
    "ok done", "okay done", "yes done", "yeah done", "yep done",
})


class TodoStore:
    """In-memory todo list, one per AIAgent. List position is priority; items are
    ``{id, content, status, parent?}`` — ``parent`` nests a subtask."""

    def __init__(self):
        self._items: List[Dict[str, str]] = []
        self._revision = 0
        self._user_confirmed: set[str] = set()

    def _fresh_items(self, todos: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Validate, dedupe and order a whole new list (replace / restore)."""
        return self._normalize_order([self._validate(t) for t in self._dedupe_by_id(todos)])

    def write(self, todos: List[Dict[str, Any]], merge: bool = False) -> List[Dict[str, str]]:
        """Replace the list (default) or merge by id; returns the full list after writing."""
        before = self.read()
        if merge:
            self._merge(todos)
        else:
            self._items = self._fresh_items(todos)
        del self._items[MAX_TODO_ITEMS:]  # keep the priority head; replays can't grow unbounded
        self._sanitize_parents(self._items)
        for item in self._items:
            if item["status"] == "completed":
                self._user_confirmed.add(item["id"])
        if self._items != before:
            self._revision += 1
        return self.read()

    def _merge(self, todos: List[Dict[str, Any]]) -> None:
        """Update existing items only in the fields provided; append new ones (validated)."""
        existing = {item["id"]: item for item in self._items}
        for t in self._dedupe_by_id(todos):
            item_id = str(t.get("id", "")).strip()
            if not item_id:
                continue  # can't merge without an id
            cur = existing.get(item_id)
            if cur is None:
                validated = self._validate(t)
                existing[validated["id"]] = validated
                self._items.append(validated)
                continue
            if t.get("content"):
                cur["content"] = self._cap_content(str(t["content"]).strip())
            if t.get("status") and str(t["status"]).strip().lower() in VALID_STATUSES:
                cur["status"] = str(t["status"]).strip().lower()
            if "parent" in t:
                parent = str(t["parent"] or "").strip()
                if parent:
                    cur["parent"] = parent
                else:
                    cur.pop("parent", None)
        # Rebuild preserving original order for existing items (first occurrence wins).
        rebuilt = {item["id"]: existing.get(item["id"], item) for item in self._items}
        self._items = self._normalize_order(list(rebuilt.values()))

    def read(self) -> List[Dict[str, str]]:
        return [item.copy() for item in self._items]

    def has_items(self) -> bool:
        return bool(self._items)

    def snapshot(self) -> Dict[str, Any]:
        """Full state clients can reconcile atomically."""
        return {
            "todos": self.read(),
            "revision": self._revision,
            "user_confirmed": sorted(self._user_confirmed),
            "keep_open": self.keep_open(),
        }

    def keep_open(self) -> bool:
        """True while any item still needs the user's completion check."""
        return any(item["status"] in _ACTIVE_STATUSES for item in self._items)

    def next_id(self) -> str:
        used = {item["id"] for item in self._items}
        n = 1
        while str(n) in used:
            n += 1
        return str(n)

    def sanitize_agent_todos(self, todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Strip agent-authored ``completed`` unless the user already confirmed that id."""
        existing = {item["id"]: item for item in self._items}
        out: List[Dict[str, Any]] = []
        for raw in todos:
            if not isinstance(raw, dict):
                out.append(raw)
                continue
            item = dict(raw)
            tid = str(item.get("id", "")).strip()
            status = str(item.get("status", "")).strip().lower()
            if status == "completed" and tid not in self._user_confirmed:
                prev = existing.get(tid)
                item["status"] = (
                    prev["status"] if prev and prev["status"] != "completed" else "in_progress"
                )
            out.append(item)
        return out

    def confirm_ids(self, ids: List[str]) -> List[str]:
        """Mark the given ids completed because the user said so. Returns confirmed ids."""
        existing = {item["id"] for item in self._items}
        confirmed: List[str] = []
        seen: set[str] = set()
        for raw in ids:
            tid = str(raw).strip()
            if not tid or tid in seen or tid not in existing:
                continue
            seen.add(tid)
            self._user_confirmed.add(tid)
            confirmed.append(tid)
        if confirmed:
            self.write([{"id": tid, "status": "completed"} for tid in confirmed], merge=True)
        return confirmed

    def add_item(self, content: str, parent: Optional[str] = None) -> List[Dict[str, str]]:
        item: Dict[str, Any] = {
            "id": self.next_id(),
            "content": self._cap_content((content or "").strip()) or "(no description)",
            "status": "pending",
        }
        parent_id = str(parent or "").strip()
        if parent_id:
            item["parent"] = parent_id
        return self.write([item], merge=True)

    def delete_ids(self, ids: List[str]) -> List[Dict[str, str]]:
        drop = {str(i).strip() for i in ids if str(i).strip()}
        if not drop:
            return self.read()
        before = [item["id"] for item in self._items]
        self._items = [item for item in self._items if item["id"] not in drop]
        self._user_confirmed -= drop
        self._sanitize_parents(self._items)
        if [item["id"] for item in self._items] != before:
            self._revision += 1
        return self.read()

    def restore(self, todos: List[Dict[str, Any]], *, revision: Any = 0,
                user_confirmed: Any = None) -> List[Dict[str, str]]:
        """Restore a trusted snapshot without manufacturing a new revision."""
        self._items = self._fresh_items(todos)[:MAX_TODO_ITEMS]
        try:
            self._revision = max(0, int(revision or 0))
        except (TypeError, ValueError):
            self._revision = 0
        if user_confirmed is None:
            self._user_confirmed = {
                item["id"] for item in self._items if item["status"] == "completed"
            }
        else:
            self._user_confirmed = {
                str(x).strip() for x in (user_confirmed or []) if str(x).strip()
            }
        return self.read()

    def format_for_injection(self) -> Optional[str]:
        """Render the list for post-compression injection, or None if nothing active. Only
        pending/in_progress items are injected — finished ones make the model re-do work after
        compression. A parent is kept (with its real status marker) when any descendant is
        active so subtasks keep context."""
        if not self._items:
            return None
        children: Dict[str, List[Dict[str, str]]] = {}
        for item in self._items:
            if item.get("parent"):
                children.setdefault(item["parent"], []).append(item)

        def render(item: Dict[str, str], depth: int, out: List[str]) -> bool:
            kid_lines: List[str] = []
            has_active_kid = False
            for kid in children.get(item["id"], []):
                has_active_kid |= render(kid, depth + 1, kid_lines)
            keep = item["status"] in _ACTIVE_STATUSES or has_active_kid
            if keep:
                marker = _STATUS_MARKERS.get(item["status"], "[?]")
                out.append(f"{'  ' * depth}- {marker} {item['id']}. "
                           f"{item['content']} ({item['status']})")
                out.extend(kid_lines)
            return keep

        lines = [TODO_INJECTION_HEADER]
        for item in self._items:
            if not item.get("parent"):
                render(item, 0, lines)
        return "\n".join(lines) if len(lines) > 1 else None

    @staticmethod
    def _cap_content(content: str) -> str:
        """Truncate to MAX_TODO_CONTENT_CHARS keeping the head (the actionable part) + marker."""
        if len(content) > MAX_TODO_CONTENT_CHARS:
            return content[:MAX_TODO_CONTENT_CHARS - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER
        return content

    @staticmethod
    def _validate(item: Dict[str, Any]) -> Dict[str, str]:
        """Normalize one item to ``{id, content, status, parent?}`` (placeholders when missing)."""
        if not isinstance(item, dict):
            return {"id": "?", "content": "(invalid item)", "status": "pending"}
        item_id = str(item.get("id", "")).strip() or "?"
        content = str(item.get("content", "")).strip()
        status = str(item.get("status", "pending")).strip().lower()
        result = {"id": item_id,
                  "content": TodoStore._cap_content(content) if content else "(no description)",
                  "status": status if status in VALID_STATUSES else "pending"}
        parent = str(item.get("parent") or "").strip()
        if parent and parent != item_id:
            result["parent"] = parent
        return result

    @staticmethod
    def _sanitize_parents(items: List[Dict[str, str]]) -> None:
        """Drop dangling parent refs and break cycles in place (such items become roots)."""
        by_id = {item["id"]: item for item in items}
        for item in items:
            if item.get("parent") and item["parent"] not in by_id:
                item.pop("parent", None)
        for item in items:
            seen, node = {item["id"]}, item
            while node.get("parent"):
                if node["parent"] in seen:
                    item.pop("parent", None)
                    break
                seen.add(node["parent"])
                node = by_id[node["parent"]]

    @staticmethod
    def _dedupe_by_id(todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Collapse duplicate ids, keeping the last occurrence in its position."""
        last_index: Dict[str, int] = {}
        for i, item in enumerate(todos):  # non-dicts get a synthetic key; _validate handles them
            key = str(item.get("id", "")).strip() if isinstance(item, dict) else f"__invalid_{i}"
            last_index[key or "?"] = i
        return [todos[i] for i in sorted(last_index.values())]

    @staticmethod
    def _normalize_order(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Lift the in_progress step ahead of any earlier pending placeholder. Nested lists
        keep authored order — reordering would tear a subtask from its siblings."""
        statuses = [item["status"] for item in items]
        if any(item.get("parent") for item in items) or "in_progress" not in statuses:
            return items
        active_index = statuses.index("in_progress")
        if "pending" not in statuses[:active_index]:
            return items
        normalized = items.copy()
        normalized.insert(statuses.index("pending"), normalized.pop(active_index))
        return normalized


def confirm_from_user_text(store: TodoStore, text: str) -> List[str]:
    """Confirm matching tasks from a user chat line. Empty when the line is a new ask."""
    if store is None or not isinstance(text, str) or not store.has_items():
        return []
    raw = text.strip()
    if not raw:
        return []
    items = store.read()
    by_id = {item["id"]: item for item in items}
    incomplete = [item for item in items if item["status"] in _ACTIVE_STATUSES]
    if not incomplete:
        return []

    found: List[str] = []
    if _CONFIRM_ALL.match(raw) or raw.lower() in _BARE_DONE:
        if re.search(r"\b(?:all|everything)\b", raw, re.I):
            found = [item["id"] for item in incomplete]
        else:
            in_progress = [item["id"] for item in incomplete if item["status"] == "in_progress"]
            if in_progress:
                found = in_progress
            elif len(incomplete) == 1:
                found = [incomplete[0]["id"]]
    else:
        tokens: List[str] = []
        for rx in (_MARK_DONE, _TASK_ID_DONE, _NUM_DONE):
            tokens.extend(match.group(1).strip().strip("\"'") for match in rx.finditer(raw))
        for token in tokens:
            if token in by_id:
                found.append(token)
                continue
            low = token.lower()
            found.extend(
                item["id"] for item in incomplete
                if low and (low in item["content"].lower() or item["content"].lower() in low)
            )

    seen: set[str] = set()
    ids: List[str] = []
    for tid in found:
        if tid in seen or tid not in by_id or by_id[tid]["status"] not in _ACTIVE_STATUSES:
            continue
        seen.add(tid)
        ids.append(tid)
    return store.confirm_ids(ids)


def todo_tool(todos: Optional[List[Dict[str, Any]]] = None, merge: bool = False,
              store: Optional[TodoStore] = None) -> str:
    """Write ``todos`` (replace, or ``merge`` by id) or read when None -> list + summary JSON."""
    if store is None:
        return tool_error("TodoStore not initialized")
    if todos is None:
        items = store.read()
    else:
        if isinstance(todos, str):  # LLMs sometimes send a JSON string instead of a list
            try:
                todos = json.loads(todos)
            except (json.JSONDecodeError, TypeError):
                return tool_error("todos must be a list of objects, got unparseable string")
        if not isinstance(todos, list):
            return tool_error(f"todos must be a list, got {type(todos).__name__}")
        items = store.write(store.sanitize_agent_todos(todos), merge)
    summary = {"total": len(items)}
    for status in ("pending", "in_progress", "completed", "cancelled"):
        summary[status] = sum(1 for i in items if i["status"] == status)
    return json.dumps({"todos": items, "revision": store.snapshot()["revision"],
                       "summary": summary}, ensure_ascii=False)


def check_todo_requirements() -> bool:
    """Todo tool has no external requirements -- always available."""
    return True


# Behavioral guidance is baked into the (static, cached) description; item shape and merge
# semantics live ONLY in the parameter schema.
TODO_SCHEMA = {
    "name": "todo_list",
    "description": (
        # See #95681.
        "Track a task list for multi-step work (3+ steps). Use for complex tasks "
        "with 3+ steps or when the user provides multiple tasks. "
        "For 'all N items' tasks, enumerate every instance as its own checklist "
        "item so none are silently dropped. "
        "Call with no parameters to read the current list.\n"
        "List order is priority. Only ONE item in_progress at a time. "
        "Break large phases into subtasks via parent. "
        "Do NOT mark an item completed. The user confirms completion by saying "
        "done/complete (or using the Desktop task list). You may set pending or "
        "in_progress only. If something fails, cancel it and add a revised "
        "item. Always returns the full current list."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "description": "Task items to write.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string"
                        },
                        "content": {
                            "type": "string",
                            "description": "Task description"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "cancelled"]
                        },
                        "parent": {
                            "type": "string",
                            "description": "Optional id of another item, making this a nested subtask. Omit for top-level."
                        }
                    },
                    "required": ["id", "content", "status"]
                }
            },
            "merge": {
                "type": "boolean",
                "description": (
                    "true: update existing items by id, add new ones. "
                    "false (default): replace the entire list with a fresh plan."
                ),
                "default": False
            }
        },
        "required": []
    }
}


from tools.registry import registry, tool_error

registry.register(
    name="todo_list", toolset="todo", schema=TODO_SCHEMA, check_fn=check_todo_requirements,
    handler=lambda args, **kw: todo_tool(
        todos=args.get("todos"), merge=args.get("merge", False), store=kw.get("store")),
    emoji="📋")
