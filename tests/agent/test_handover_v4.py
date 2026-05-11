import json

import pytest

from agent.adaptive_routing import AdaptiveRoutingError, parse_router_response, resolve_route
from agent.fallback_triggers import is_enabled_trigger, trigger_for_error
from agent.spend_governance import record_spend, spend_db_path
from hermes_cli.config import DEFAULT_CONFIG
from hermes_cli.profiles import create_profile


def test_handover_defaults_are_disabled():
    assert DEFAULT_CONFIG["hermes_features"]["handover_schema"] == 4
    assert DEFAULT_CONFIG["adaptive_routing"]["enabled"] is False
    assert DEFAULT_CONFIG["emergency_fallback"]["enabled"] is False
    assert DEFAULT_CONFIG["spend_governance"]["enabled"] is False
    assert DEFAULT_CONFIG["profile_routing"]["enabled"] is False
    assert DEFAULT_CONFIG["org_escalation"]["enabled"] is False
    assert DEFAULT_CONFIG["kanban"]["orchestrator_mode"] is False


def test_router_response_requires_json_only_allowlisted_consultant():
    raw = json.dumps({
        "tier": "consultant",
        "target_model": "openai/gpt-5.5",
        "reason_code": "complex_planning",
        "approval": True,
        "router_notes": "needs a stronger model",
    })
    decision = parse_router_response(raw, consultant_allowlist=["openai/gpt-5.5"])
    assert decision.tier == "consultant"
    assert decision.target_model == "openai/gpt-5.5"

    with pytest.raises(AdaptiveRoutingError):
        parse_router_response(raw, consultant_allowlist=["openai/gpt-5.4-mini"])


def test_adaptive_router_falls_back_to_baseline_on_invalid_output():
    cfg = {
        "enabled": True,
        "provider": "openrouter",
        "baseline_model": "openai/gpt-5.4-mini",
        "router_model": "openai/gpt-5.5",
        "consultant_models_allowlist": [],
    }
    decision = resolve_route(
        cfg,
        current_model="openai/gpt-5.4-mini",
        user_message="hello",
        call_router=lambda *_args: "not json",
    )
    assert decision.tier == "baseline"
    assert decision.target_model == "openai/gpt-5.4-mini"
    assert decision.reason_code == "router_failure"


def test_fallback_trigger_mapping():
    class RateLimitError(Exception):
        status_code = 429

    trigger = trigger_for_error(RateLimitError("too many requests"))
    assert trigger == "rate_limit"
    assert is_enabled_trigger(trigger, ["rate_limit"])
    assert not is_enabled_trigger(trigger, ["billing_error"])


def test_spend_governance_persists_under_hermes_home(monkeypatch, tmp_path):
    hermes_home = tmp_path / ".hermes"
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    cfg = {
        "enabled": True,
        "aggregate_delegation": True,
        "persist_path": "",
        "soft_cap": {"per_turn_usd": 1.0},
        "hard_cap": {"per_turn_usd": 2.0},
    }
    snapshots = record_spend(
        cfg,
        amount_usd=0.25,
        session_id="child",
        parent_session_id="parent",
        model="openai/gpt-5.4-mini",
        provider="openrouter",
    )
    assert spend_db_path(cfg) == hermes_home / "state" / "spend.sqlite3"
    assert {s.period for s in snapshots} == {"turn", "day", "month"}
    assert next(s for s in snapshots if s.period == "turn").spent_usd_est == pytest.approx(0.25)


def test_ephemeral_profile_marker(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    profile_dir = create_profile(
        "temp-work",
        no_alias=True,
        no_skills=True,
        ephemeral=True,
        ttl_hours=12,
    )
    marker = profile_dir / ".ephemeral_profile"
    assert marker.exists()
    data = json.loads(marker.read_text(encoding="utf-8"))
    assert data["ttl_hours"] == 12
