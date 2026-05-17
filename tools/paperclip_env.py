"""Paperclip control-plane integration for Hermes.

The Paperclip server (`@paperclipai/server`) is a long-running Node process with
PostgreSQL and WebSockets. It should run on Fly, Railway, Render, a VPS, or
similar — not inside Vercel serverless.

Hermes + the **dot-hermes** Vercel project provide:

- ``PAPERCLIP_PUBLIC_BASE_URL`` — HTTPS origin of your real Paperclip deployment
  (also set on Vercel so ``/paperclip`` can redirect users there). If unset,
  ``PAPERCLIP_PUBLIC_URL`` (Railway’s variable name) is used as the same value.
- ``DOT_HERMES_PUBLIC_URL`` — optional; stable production URL of dot-hermes
  (e.g. ``https://dot-hermes.vercel.app``) for system-prompt hints.

See ``skills/devops/paperclip-dot-hermes-bridge/SKILL.md``.
"""

from __future__ import annotations

import logging
import os
import urllib.error
import urllib.request
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def normalize_public_base_url(raw: Optional[str]) -> Optional[str]:
    """Return https origin without trailing slash, or None if unset/invalid."""
    if not raw:
        return None
    url = str(raw).strip()
    if not url:
        return None
    url = url.rstrip("/")
    if not url.lower().startswith(("https://", "http://")):
        return None
    return url


def get_paperclip_public_base_url() -> Optional[str]:
    """Prefer Hermes name; accept Railway's ``PAPERCLIP_PUBLIC_URL`` as the same origin."""
    raw = os.environ.get("PAPERCLIP_PUBLIC_BASE_URL") or os.environ.get(
        "PAPERCLIP_PUBLIC_URL"
    )
    return normalize_public_base_url(raw)


def get_dot_hermes_public_url() -> Optional[str]:
    return normalize_public_base_url(os.environ.get("DOT_HERMES_PUBLIC_URL"))


def build_paperclip_system_hint() -> str:
    """Short block for the agent system prompt when URLs are configured."""
    direct = get_paperclip_public_base_url()
    hub = get_dot_hermes_public_url()
    if not direct and not hub:
        return ""
    lines = [
        "**Paperclip:** Human control-plane UI (agents/orchestration).",
    ]
    if hub:
        lines.append(
            f"- Vercel hub: open `{hub}/paperclip` (redirects to Paperclip when "
            "`PAPERCLIP_PUBLIC_BASE_URL` is set on the Vercel project)."
        )
    if direct:
        lines.append(f"- Paperclip deployment: `{direct}/`")
    lines.append(
        "Host the real server with Postgres (see Paperclip deploy docs); Hermes only "
        "links/proxies — it does not replace `@paperclipai/server`."
    )
    return "\n".join(lines)


def format_operator_summary() -> str:
    """Plain-text summary for `hermes paperclip`."""
    direct = get_paperclip_public_base_url()
    hub = get_dot_hermes_public_url()
    lines = [
        "Paperclip + dot-hermes",
        "",
        f"  PAPERCLIP_PUBLIC_BASE_URL: {direct or '(not set)'}",
        f"  DOT_HERMES_PUBLIC_URL:      {hub or '(not set)'}",
        "",
        "Deploy the Paperclip server on Fly/Railway/Render/VPS + Postgres, then:",
        "  - Set PAPERCLIP_PUBLIC_BASE_URL in Hermes ~/.hermes/.env",
        "  - Set the same on the Vercel dot-hermes project for /paperclip redirect",
        "",
        "Headless help (no Cursor):",
        "  hermes paperclip deploy        # Railway template URL + env steps",
        "  hermes paperclip fix-checkout # fix root-owned dist/ before pnpm install",
        "",
        "Run: hermes doctor  (checks reachability when PAPERCLIP_PUBLIC_BASE_URL is set)",
    ]
    return "\n".join(lines)


def doctor_paperclip_checks(
    check_ok: Callable[..., None],
    check_warn: Callable[..., None],
    check_fail: Callable[..., None],
    check_info: Callable[..., None],
    issues: list[str],
) -> None:
    """Optional doctor section when Paperclip-related env is present."""
    _ = check_fail  # reserved for hard failures
    pc = get_paperclip_public_base_url()
    hub = get_dot_hermes_public_url()
    if not pc and not hub:
        return
    if hub:
        check_ok("dot-hermes hub URL", f"({hub})")
    if pc:
        check_ok("Paperclip public URL", f"({pc})")
        try:
            with urllib.request.urlopen(pc + "/", timeout=12) as resp:
                code = getattr(resp, "status", None) or resp.getcode()
                if code and code < 500:
                    check_ok("Paperclip HTTP (GET)", f"({code})")
                else:
                    check_warn("Paperclip HTTP (GET)", f"status {code}")
        except urllib.error.HTTPError as e:
            if e.code and e.code < 500:
                check_ok("Paperclip HTTP (GET)", f"({e.code})")
            else:
                check_warn("Paperclip HTTP", str(e)[:160])
                logger.debug("paperclip doctor HTTP error: %s", e)
        except Exception as e:
            check_warn("Paperclip reachability", str(e)[:160])
            logger.debug("paperclip doctor probe failed: %s", e)
    elif hub:
        check_info(
            "Paperclip URL",
            "PAPERCLIP_PUBLIC_BASE_URL not set — configure it for /paperclip redirect + doctor checks",
        )

    try:
        from tools.paperclip_checkout import doctor_checkout_permission_warning

        co_warn = doctor_checkout_permission_warning()
        if co_warn:
            check_warn("Paperclip monorepo checkout", co_warn[:240])
            issues.append("Run: hermes paperclip fix-checkout (then pnpm install)")
    except Exception:
        pass
