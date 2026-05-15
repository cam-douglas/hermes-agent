"""Tests for autoresearch ``program.md`` outer runtime helpers."""

from pathlib import Path

import pytest

from tools.autoresearch_runtime import (
    format_autoresearch_train_commands,
    load_autoresearch_outer_runtime_minutes,
    parse_outer_runtime_minutes,
    resolve_autoresearch_program_path,
)


class TestParseOuterRuntimeMinutes:
    def test_outer_runtime_phrase(self):
        text = "# Autoresearch\n\nOuter runtime: 45 minutes\n"
        assert parse_outer_runtime_minutes(text) == 45

    def test_minutes_total(self):
        text = "# autoresearch\n\nBudget is 120 minutes total.\n"
        assert parse_outer_runtime_minutes(text) == 120

    def test_no_match_returns_none(self):
        assert parse_outer_runtime_minutes("# autoresearch\n\nNo duration here.\n") is None


class TestLoadAutoresearchOuterRuntime:
    def test_env_wins(self, tmp_path, monkeypatch):
        monkeypatch.delenv("HERMES_AUTORESEARCH_PROGRAM", raising=False)
        p = tmp_path / "program.md"
        p.write_text("# autoresearch\n\nOuter runtime: 10 minutes\n")
        monkeypatch.setenv("HERMES_AUTORESEARCH_PROGRAM", str(p))
        monkeypatch.setenv("HERMES_AUTORESEARCH_OUTER_MINUTES", "99")
        assert load_autoresearch_outer_runtime_minutes() == (
            99,
            "env:HERMES_AUTORESEARCH_OUTER_MINUTES",
        )

    def test_default_600_when_marker_only(self, tmp_path, monkeypatch):
        monkeypatch.delenv("HERMES_AUTORESEARCH_OUTER_MINUTES", raising=False)
        p = tmp_path / "program.md"
        p.write_text("# autoresearch\n\nExperiment brief.\n")
        monkeypatch.setenv("HERMES_AUTORESEARCH_PROGRAM", str(p))
        prov = str(p.resolve())
        assert load_autoresearch_outer_runtime_minutes() == (600, prov)

    def test_explicit_from_program(self, tmp_path, monkeypatch):
        monkeypatch.delenv("HERMES_AUTORESEARCH_OUTER_MINUTES", raising=False)
        p = tmp_path / "program.md"
        p.write_text("# autoresearch\n\nWall-clock budget 33 minutes.\n")
        monkeypatch.setenv("HERMES_AUTORESEARCH_PROGRAM", str(p))
        assert load_autoresearch_outer_runtime_minutes() == (33, str(p.resolve()))

    def test_not_autoresearch_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.delenv("HERMES_AUTORESEARCH_OUTER_MINUTES", raising=False)
        p = tmp_path / "program.md"
        p.write_text("# Other project\n\nOuter runtime 10 minutes\n")
        monkeypatch.setenv("HERMES_AUTORESEARCH_PROGRAM", str(p))
        assert load_autoresearch_outer_runtime_minutes() is None


class TestResolveProgramPath:
    def test_implicit_canonical_skipped_by_default(self, tmp_path, monkeypatch):
        from tools import autoresearch_runtime as ar

        monkeypatch.delenv("HERMES_AUTORESEARCH_PROGRAM", raising=False)
        monkeypatch.delenv("HERMES_AUTORESEARCH_OUTER_MINUTES", raising=False)
        monkeypatch.delenv("HERMES_AUTORESEARCH_IMPLICIT_CANONICAL", raising=False)
        home = tmp_path
        monkeypatch.setattr(ar, "_get_hermes_home", lambda: home)
        checkout = home / "skills/software-development/repo-autoresearch-cpu/checkout"
        checkout.mkdir(parents=True)
        (checkout / "program.md").write_text("# autoresearch\n\nx\n")
        assert resolve_autoresearch_program_path() is None
        assert load_autoresearch_outer_runtime_minutes() is None

    def test_implicit_canonical_when_opt_in_env(self, tmp_path, monkeypatch):
        from tools import autoresearch_runtime as ar

        monkeypatch.delenv("HERMES_AUTORESEARCH_PROGRAM", raising=False)
        monkeypatch.delenv("HERMES_AUTORESEARCH_OUTER_MINUTES", raising=False)
        monkeypatch.setenv("HERMES_AUTORESEARCH_IMPLICIT_CANONICAL", "1")
        home = tmp_path
        monkeypatch.setattr(ar, "_get_hermes_home", lambda: home)
        checkout = home / "skills/software-development/repo-autoresearch-cpu/checkout"
        checkout.mkdir(parents=True)
        p = checkout / "program.md"
        p.write_text("# autoresearch\n\nOuter runtime: 9 minutes\n")
        assert resolve_autoresearch_program_path(scope_key="any") == p.resolve()
        assert load_autoresearch_outer_runtime_minutes(scope_key="any") == (
            9,
            str(p.resolve()),
        )

    def test_engaged_scope_allows_canonical_without_implicit(
        self, tmp_path, monkeypatch
    ):
        from tools import autoresearch_runtime as ar

        monkeypatch.delenv("HERMES_AUTORESEARCH_PROGRAM", raising=False)
        monkeypatch.delenv("HERMES_AUTORESEARCH_OUTER_MINUTES", raising=False)
        monkeypatch.delenv("HERMES_AUTORESEARCH_IMPLICIT_CANONICAL", raising=False)
        home = tmp_path
        monkeypatch.setattr(ar, "_get_hermes_home", lambda: home)
        checkout = home / "skills/software-development/repo-autoresearch-cpu/checkout"
        checkout.mkdir(parents=True)
        p = checkout / "program.md"
        p.write_text("# autoresearch\n\nOuter runtime: 7 minutes\n")
        ar.set_autoresearch_engaged_scope("chat-alpha")
        assert resolve_autoresearch_program_path(scope_key="chat-alpha") == p.resolve()
        assert resolve_autoresearch_program_path(scope_key="chat-beta") is None
        assert load_autoresearch_outer_runtime_minutes(scope_key="chat-alpha") == (
            7,
            str(p.resolve()),
        )
        ar.clear_autoresearch_engaged_scope()

    def test_implicit_canonical_suppressed_on_messaging_gateway(
        self, tmp_path, monkeypatch
    ):
        from tools import autoresearch_runtime as ar

        monkeypatch.delenv("HERMES_AUTORESEARCH_PROGRAM", raising=False)
        monkeypatch.delenv("HERMES_AUTORESEARCH_OUTER_MINUTES", raising=False)
        monkeypatch.setenv("HERMES_AUTORESEARCH_IMPLICIT_CANONICAL", "1")
        home = tmp_path
        monkeypatch.setattr(ar, "_get_hermes_home", lambda: home)
        checkout = home / "skills/software-development/repo-autoresearch-cpu/checkout"
        checkout.mkdir(parents=True)
        p = checkout / "program.md"
        p.write_text("# autoresearch\n\nOuter runtime: 9 minutes\n")
        assert resolve_autoresearch_program_path(
            scope_key="any", messaging_gateway=True
        ) is None
        assert load_autoresearch_outer_runtime_minutes(
            scope_key="any", messaging_gateway=True
        ) is None

    def test_outer_minutes_env_suppressed_on_messaging_without_engagement(
        self, monkeypatch
    ):
        from tools import autoresearch_runtime as ar

        monkeypatch.setenv("HERMES_AUTORESEARCH_OUTER_MINUTES", "500")
        monkeypatch.delenv("HERMES_AUTORESEARCH_PROGRAM", raising=False)
        assert load_autoresearch_outer_runtime_minutes(
            scope_key="sms:dm:1", messaging_gateway=True
        ) is None
        ar.set_autoresearch_engaged_scope("sms:dm:1")
        assert load_autoresearch_outer_runtime_minutes(
            scope_key="sms:dm:1", messaging_gateway=True
        ) == (500, "env:HERMES_AUTORESEARCH_OUTER_MINUTES")
        ar.clear_autoresearch_engaged_scope()

    def test_missing_env_file(self, monkeypatch):
        monkeypatch.setenv("HERMES_AUTORESEARCH_PROGRAM", "/nonexistent/program.md")
        assert resolve_autoresearch_program_path() is None

    def test_env_file(self, tmp_path, monkeypatch):
        p = tmp_path / "program.md"
        p.write_text("x")
        monkeypatch.setenv("HERMES_AUTORESEARCH_PROGRAM", str(p))
        assert resolve_autoresearch_program_path() == p.resolve()


class TestWallclockStateFile:
    def test_persist_and_clear(self, tmp_path, monkeypatch):
        from tools import autoresearch_runtime as ar

        monkeypatch.setattr(ar, "_get_hermes_home", lambda: tmp_path)
        ar.persist_autoresearch_wallclock_state(
            session_id="sess_test",
            deadline_epoch=12345.0,
            budget_minutes=42,
            provenance="/tmp/p.md",
        )
        state = tmp_path / ar.AUTORESEARCH_WALLCLOCK_STATE_FILENAME
        assert state.is_file()
        text = state.read_text(encoding="utf-8")
        assert "sess_test" in text
        assert "hermes logs -f" in text
        assert "train_recommended_cmd" in text
        assert "timeout" in text
        ar.clear_autoresearch_wallclock_state()
        assert not state.is_file()


class TestFormatTrainCommands:
    def test_uses_python3_not_uv_in_recommended(self, tmp_path):
        checkout = tmp_path / "co"
        checkout.mkdir()
        cmds = format_autoresearch_train_commands(checkout_dir=checkout, budget_minutes=10)
        assert "train_recommended_cmd" in cmds
        assert "python3 train.py" in cmds["train_recommended_cmd"]
        assert "timeout 600" in cmds["train_recommended_cmd"]
        assert "HERMES_AUTORESEARCH_OUTER_MINUTES=10" in cmds["train_recommended_cmd"]
        assert "prepare_recommended_cmd" in cmds
        assert "prepare.py" in cmds["prepare_recommended_cmd"]

    def test_prefers_dot_venv_python(self, tmp_path):
        checkout = tmp_path / "co"
        vpy = checkout / ".venv" / "bin" / "python"
        vpy.parent.mkdir(parents=True)
        vpy.write_text("#")
        cmds = format_autoresearch_train_commands(checkout_dir=checkout, budget_minutes=5)
        assert str(vpy.resolve()) in cmds["train_recommended_cmd"]
