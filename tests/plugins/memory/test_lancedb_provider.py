"""Tests for LanceDB memory provider."""

from __future__ import annotations

import json
import os
import sys

import pytest

pytest.importorskip("lancedb")


@pytest.fixture()
def provider(tmp_path, monkeypatch):
    """Fresh Hermes home + initialized LanceDB provider."""
    from plugins.memory.lancedb import LanceDBMemoryProvider

    home = tmp_path / ".hermes"
    home.mkdir(parents=True)
    store = tmp_path / "ldb"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr("hermes_constants.get_hermes_home", lambda: home)

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    p = LanceDBMemoryProvider()
    monkeypatch.setenv("LANCEDB_URI", str(store))
    monkeypatch.delenv("LANCEDB_EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    p.initialize("sess-1", user_id="u1", agent_identity="prof")
    return p


def test_is_available():
    from plugins.memory.lancedb import LanceDBMemoryProvider

    assert LanceDBMemoryProvider().is_available() is True


def test_remember_and_keyword_search(provider):
    raw = provider.handle_tool_call("lancedb_remember", {"text": "User prefers dark mode terminals"})
    assert "Stored" in raw
    raw_search = provider.handle_tool_call("lancedb_search", {"query": "dark mode", "top_k": 5})
    data = json.loads(raw_search)
    assert data.get("count", 0) >= 1
    assert any("dark" in (item.get("text") or "").lower() for item in data.get("results", []))


def test_profile_lists_rows(provider):
    provider.handle_tool_call("lancedb_remember", {"text": "Note alpha"})
    raw = provider.handle_tool_call("lancedb_profile", {})
    data = json.loads(raw)
    assert "alpha" in data.get("result", "")
