"""Emergency fallback trigger taxonomy for handover v4."""

from __future__ import annotations

from typing import Iterable

from agent.error_classifier import FailoverReason


_BILLING_PATTERNS = (
    "insufficient credits",
    "billing",
    "payment required",
    "quota exceeded",
    "quota_exceeded",
)


def trigger_for_error(error: BaseException, *, reason: FailoverReason | None = None) -> str | None:
    """Map an API error/classified reason into a handover trigger name."""
    if reason == FailoverReason.rate_limit:
        return "rate_limit"
    if reason == FailoverReason.billing:
        return "billing_error"

    status = getattr(error, "status_code", None)
    if status == 429:
        return "rate_limit"
    if status == 402:
        return "billing_error"

    text = str(error or "").lower()
    if "rate limit" in text or "429" in text:
        return "rate_limit"
    if any(p in text for p in _BILLING_PATTERNS):
        return "quota_exceeded" if "quota" in text else "billing_error"
    return None


def is_enabled_trigger(trigger: str | None, configured: Iterable[str] | None) -> bool:
    if not trigger:
        return False
    enabled = set(configured or [])
    return trigger in enabled
