"""Tests for Paperclip / dot-hermes URL helpers."""

from tools import paperclip_env as pe


def test_normalize_public_base_url():
    assert pe.normalize_public_base_url(None) is None
    assert pe.normalize_public_base_url("") is None
    assert pe.normalize_public_base_url("  ") is None
    assert pe.normalize_public_base_url("example.com") is None
    assert pe.normalize_public_base_url("https://x.test/path/") == "https://x.test/path"


def test_build_paperclip_system_hint_empty(monkeypatch):
    monkeypatch.delenv("PAPERCLIP_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("DOT_HERMES_PUBLIC_URL", raising=False)
    assert pe.build_paperclip_system_hint() == ""


def test_build_paperclip_system_hint_with_urls(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_PUBLIC_BASE_URL", "https://pc.example/")
    monkeypatch.setenv("DOT_HERMES_PUBLIC_URL", "https://dot.example")
    text = pe.build_paperclip_system_hint()
    assert "dot.example" in text
    assert "pc.example" in text


def test_format_operator_summary(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_PUBLIC_BASE_URL", "https://pc.example")
    monkeypatch.delenv("DOT_HERMES_PUBLIC_URL", raising=False)
    out = pe.format_operator_summary()
    assert "PAPERCLIP_PUBLIC_BASE_URL:" in out
    assert "pc.example" in out


def test_get_paperclip_public_base_url_falls_back_to_public_url(monkeypatch):
    monkeypatch.delenv("PAPERCLIP_PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("PAPERCLIP_PUBLIC_URL", "https://pc.railway.app/")
    assert pe.get_paperclip_public_base_url() == "https://pc.railway.app"
