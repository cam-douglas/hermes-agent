"""Disabled-by-default adaptive model routing for handover v4.

This module is intentionally small and side-effect free except for the optional
router LLM call.  The runtime owns the model/client swap; this helper validates
configuration, parses router JSON, and returns a compact decision object.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class RoutingDecision:
    tier: str
    target_model: str
    reason_code: str
    approval: bool | None = None
    router_notes: str = ""
    router_model: str = ""
    latency_ms: int = 0
    error: str | None = None


class AdaptiveRoutingError(ValueError):
    """Raised for invalid router output or unsafe consultant selection."""


def _strip_json_fence(text: str) -> str:
    raw = (text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw


def parse_router_response(text: str, *, consultant_allowlist: list[str]) -> RoutingDecision:
    """Parse and validate the handover v4 router JSON contract."""
    try:
        data = json.loads(_strip_json_fence(text))
    except json.JSONDecodeError as exc:
        raise AdaptiveRoutingError(f"router_json_invalid: {exc}") from exc
    if not isinstance(data, dict):
        raise AdaptiveRoutingError("router_json_not_object")

    allowed_keys = {"tier", "target_model", "reason_code", "approval", "router_notes"}
    extra = set(data) - allowed_keys
    if extra:
        raise AdaptiveRoutingError(f"router_json_extra_keys: {sorted(extra)}")

    tier = data.get("tier")
    target_model = data.get("target_model")
    reason_code = data.get("reason_code")
    if tier not in {"baseline", "consultant"}:
        raise AdaptiveRoutingError("router_tier_invalid")
    if not isinstance(target_model, str) or not target_model.strip():
        raise AdaptiveRoutingError("router_target_model_invalid")
    if not isinstance(reason_code, str) or not reason_code.strip():
        raise AdaptiveRoutingError("router_reason_code_invalid")

    approval = data.get("approval")
    if tier == "consultant":
        if approval is not True:
            raise AdaptiveRoutingError("consultant_requires_approval")
        if target_model not in set(consultant_allowlist or []):
            raise AdaptiveRoutingError("consultant_model_not_allowlisted")
    elif approval is not None and not isinstance(approval, bool):
        raise AdaptiveRoutingError("router_approval_invalid")

    notes = data.get("router_notes", "")
    if notes is not None and not isinstance(notes, str):
        raise AdaptiveRoutingError("router_notes_invalid")
    if isinstance(notes, str) and len(notes) > 500:
        notes = notes[:500]

    return RoutingDecision(
        tier=tier,
        target_model=target_model.strip(),
        reason_code=reason_code.strip(),
        approval=approval if isinstance(approval, bool) else None,
        router_notes=notes or "",
    )


def disabled_decision(config: Mapping[str, Any], current_model: str) -> RoutingDecision:
    return RoutingDecision(
        tier="baseline",
        target_model=current_model,
        reason_code="routing_disabled",
        router_model=str(config.get("router_model") or ""),
    )


def fallback_decision(config: Mapping[str, Any], reason: str, *, latency_ms: int = 0) -> RoutingDecision:
    return RoutingDecision(
        tier="baseline",
        target_model=str(config.get("baseline_model") or ""),
        reason_code=reason,
        router_model=str(config.get("router_model") or ""),
        latency_ms=latency_ms,
        error=reason,
    )


def resolve_route(
    config: Mapping[str, Any],
    *,
    current_model: str,
    user_message: str,
    call_router: Callable[[list[dict[str, str]], str, float], str] | None,
) -> RoutingDecision:
    """Resolve a route for the current turn.

    ``call_router`` is injected by the runtime to keep this module independent
    of OpenAI client construction.  It receives messages, model, timeout.
    """
    if not isinstance(config, Mapping) or not config.get("enabled"):
        return disabled_decision(config or {}, current_model)

    provider = str(config.get("provider") or "").strip().lower()
    if provider != "openrouter":
        return fallback_decision(config, "routing_provider_unsupported")

    baseline = str(config.get("baseline_model") or current_model).strip() or current_model
    router_model = str(config.get("router_model") or "").strip()
    if not router_model or call_router is None:
        return RoutingDecision(
            tier="baseline",
            target_model=baseline,
            reason_code="router_unavailable",
            router_model=router_model,
        )

    prompt = (
        "You are a Hermes model router. Return JSON only with keys "
        "tier, target_model, reason_code, approval, router_notes. Choose "
        "tier=baseline unless the task clearly needs a consultant model."
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_message[:8000]},
    ]
    started = time.perf_counter()
    try:
        raw = call_router(
            messages,
            router_model,
            float(config.get("router_timeout_seconds") or 45),
        )
        decision = parse_router_response(
            raw,
            consultant_allowlist=list(config.get("consultant_models_allowlist") or []),
        )
        object.__setattr__(decision, "router_model", router_model)
        object.__setattr__(decision, "latency_ms", int((time.perf_counter() - started) * 1000))
        if decision.tier == "baseline" and not decision.target_model:
            object.__setattr__(decision, "target_model", baseline)
        return decision
    except Exception as exc:
        return RoutingDecision(
            tier="baseline",
            target_model=baseline,
            reason_code="router_failure",
            router_model=router_model,
            latency_ms=int((time.perf_counter() - started) * 1000),
            error=str(exc),
        )


def status_payload(decision: RoutingDecision) -> dict[str, Any]:
    return {
        "resolved_tier": decision.tier,
        "resolved_model": decision.target_model,
        "reason_code": decision.reason_code,
        "consultant_approved": decision.approval if decision.tier == "consultant" else None,
        "router_model": decision.router_model,
        "latency_ms": decision.latency_ms,
    }
