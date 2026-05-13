"""Tests for tools.vercel_env Vercel Sandbox credential resolution."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tools.vercel_env import ensure_vercel_project_id_for_sandbox, read_nearest_vercel_project_json


def test_read_nearest_vercel_project_json_nested(tmp_path: Path) -> None:
    vercel = tmp_path / ".vercel"
    vercel.mkdir()
    data = {"projectId": "prj_x", "orgId": "team_y"}
    (vercel / "project.json").write_text(json.dumps(data), encoding="utf-8")
    sub = tmp_path / "deep" / "a"
    sub.mkdir(parents=True)
    assert read_nearest_vercel_project_json(sub) == {"projectId": "prj_x", "orgId": "team_y"}


def test_ensure_keeps_explicit_team_over_link_org(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("VERCEL_OIDC_TOKEN", raising=False)
    monkeypatch.delenv("VERCEL_PROJECT_ID", raising=False)
    monkeypatch.setenv("VERCEL_TOKEN", "t")
    monkeypatch.setenv("VERCEL_TEAM_ID", "team-fixed")
    vercel = tmp_path / ".vercel"
    vercel.mkdir()
    (vercel / "project.json").write_text(
        '{"projectId":"prj_link","orgId":"team_from_file"}', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    assert ensure_vercel_project_id_for_sandbox() == "prj_link"
    assert os.environ["VERCEL_PROJECT_ID"] == "prj_link"
    assert os.environ["VERCEL_TEAM_ID"] == "team-fixed"


def test_ensure_sets_team_from_link_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("VERCEL_OIDC_TOKEN", raising=False)
    monkeypatch.delenv("VERCEL_PROJECT_ID", raising=False)
    monkeypatch.delenv("VERCEL_TEAM_ID", raising=False)
    monkeypatch.setenv("VERCEL_TOKEN", "t")
    vercel = tmp_path / ".vercel"
    vercel.mkdir()
    (vercel / "project.json").write_text(
        '{"projectId":"prj_link","orgId":"team_from_file"}', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    assert ensure_vercel_project_id_for_sandbox() == "prj_link"
    assert os.environ["VERCEL_TEAM_ID"] == "team_from_file"
