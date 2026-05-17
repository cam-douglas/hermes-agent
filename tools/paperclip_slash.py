"""Slash command ``/paperclip`` — open or link to the configured Paperclip UI."""

from __future__ import annotations

import logging
import webbrowser

from tools.paperclip_env import get_dot_hermes_public_url, get_paperclip_public_base_url

logger = logging.getLogger(__name__)


def paperclip_slash_reply(*, open_browser: bool = False) -> str:
    """Return user-facing text; optionally open the best URL in a desktop browser.

    Prefer the dot-hermes ``/paperclip`` redirect when ``DOT_HERMES_PUBLIC_URL``
    is set so the same flow as production works locally.
    """
    direct = get_paperclip_public_base_url()
    hub = get_dot_hermes_public_url()

    lines: list[str] = []
    primary: str | None = None

    if hub:
        primary = f"{hub.rstrip('/')}/paperclip"
        lines.append(f"**Paperclip (via dot-hermes):** {primary}")
        lines.append("_Redirects to your `PAPERCLIP_PUBLIC_BASE_URL` when Vercel env is set._")
    if direct:
        lines.append(f"**Paperclip (direct):** {direct.rstrip('/')}/")
        if primary is None:
            primary = f"{direct.rstrip('/')}/"
    if hub and direct:
        lines.append("")
        lines.append(f"_Configured deployment origin:_ `{direct}`")

    if not lines:
        lines.extend(
            [
                "**Paperclip is not configured yet.**",
                "",
                "Set in `HERMES_HOME/.env`, then restart:",
                "  `PAPERCLIP_PUBLIC_BASE_URL=https://<your-hosted-paperclip-origin>`",
                "Optional hub redirect:",
                "  `DOT_HERMES_PUBLIC_URL=https://<your-dot-hermes>.vercel.app`",
                "",
                "Headless deploy: `hermes paperclip deploy`",
            ]
        )
        return "\n".join(lines).strip()

    header = (
        "Opening Paperclip in your browser (local clients only).\n"
        if open_browser and primary
        else "Paperclip links:\n"
    )
    body = "\n".join(lines)
    out = f"{header}\n{body}"

    if open_browser and primary:
        try:
            webbrowser.open(primary)
            out += "\n\n_(Launched default browser.)_"
        except Exception as e:
            logger.debug("paperclip webbrowser.open failed: %s", e)

    return out.strip()
