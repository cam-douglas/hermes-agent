"""Tests for /paperclip slash helper."""

from tools.paperclip_slash import paperclip_slash_reply


def test_paperclip_slash_reply_unconfigured(monkeypatch):
    monkeypatch.delenv("PAPERCLIP_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("PAPERCLIP_PUBLIC_URL", raising=False)
    monkeypatch.delenv("DOT_HERMES_PUBLIC_URL", raising=False)
    text = paperclip_slash_reply(open_browser=False)
    assert "not configured" in text.lower()


def test_paperclip_slash_reply_prefers_hub(monkeypatch):
    monkeypatch.delenv("PAPERCLIP_PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("DOT_HERMES_PUBLIC_URL", "https://hub.example")
    text = paperclip_slash_reply(open_browser=False)
    assert "hub.example/paperclip" in text.replace(" ", "")
