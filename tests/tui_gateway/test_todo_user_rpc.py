"""User-owned todo.* RPCs and agent completion gating through the gateway."""

from tools.todo_tool import TodoStore

import tui_gateway.server as server


def _call(method, params):
    return server._methods[method](1, params)


def test_todo_methods_are_registered():
    for name in ("todo.get", "todo.add", "todo.update", "todo.delete", "todo.confirm"):
        assert name in server._methods


def test_todo_add_update_delete_and_confirm(monkeypatch):
    store = TodoStore()

    class Agent:
        _todo_store = store

    session = {"agent": Agent()}
    events = []
    monkeypatch.setitem(server._sessions, "s1", session)
    monkeypatch.setattr(server, "_sess", lambda params, rid: (session, None))
    monkeypatch.setattr(server, "_sess_nowait", lambda params, rid: (session, None))
    monkeypatch.setattr(server, "_emit", lambda event, sid, payload=None: events.append((event, sid, payload)))

    added = _call("todo.add", {"session_id": "s1", "content": "Plus button"})
    assert added["result"]["todos"][0]["content"] == "Plus button"
    assert added["result"]["keep_open"] is True
    assert added["result"]["todos"][0]["status"] == "pending"

    updated = _call("todo.update", {"session_id": "s1", "id": "1", "content": "Plus and edit"})
    assert updated["result"]["todos"][0]["content"] == "Plus and edit"
    assert updated["result"]["todos"][0]["status"] == "pending"

    confirmed = _call("todo.confirm", {"session_id": "s1", "id": "1"})
    assert confirmed["result"]["todos"][0]["status"] == "completed"
    assert confirmed["result"]["keep_open"] is False

    store.add_item("Remove me")
    deleted = _call("todo.delete", {"session_id": "s1", "id": "2"})
    assert all(item["id"] != "2" for item in deleted["result"]["todos"])
    assert events[-1][0] == "todo.updated"
