#!/usr/bin/env python3
"""
MCP OAuth 2.1 Client Support

Implements the browser-based OAuth 2.1 authorization code flow with PKCE
for MCP servers that require OAuth authentication instead of static bearer
tokens.

Uses the MCP Python SDK's ``OAuthClientProvider`` (an ``httpx.Auth`` subclass)
which handles discovery, dynamic client registration, PKCE, token exchange,
refresh, and step-up authorization automatically.

This module provides the glue:
    - ``HermesTokenStorage``: persists tokens/client-info to disk so they
      survive across process restarts.
    - Callback server: ephemeral localhost HTTP server to capture the OAuth
      redirect with the authorization code.
    - ``build_oauth_auth()``: entry point called by ``mcp_tool.py`` that wires
      everything together and returns the ``httpx.Auth`` object.

Configuration in config.yaml::

    mcp_servers:
      my_server:
        url: "https://mcp.example.com/mcp"
        auth: oauth
        oauth:                                  # all fields optional
          client_id: "pre-registered-id"        # skip dynamic registration
          client_secret: "secret"               # confidential clients only
          scope: "read write"                   # default: server-provided
          redirect_port: 0                      # 0 = auto-pick free port
          client_name: "My Custom Client"       # default: "Hermes Agent"
          open_browser: true                    # set false to print URL only (avoids duplicate tabs on macOS)
"""

import asyncio
import json
import logging
import os
import re
import secrets
import socket
import stat
import sys
import threading
import time
import contextvars
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

# One asyncio.Lock per running event loop so concurrent OAuth flows cannot bind
# the same redirect port twice (Zapier/MCP may retry quickly after failed token
# exchange). Tests and one-off asyncio.run() each get their own loop id.
_oauth_callback_wait_locks: dict[int, asyncio.Lock] = {}

# ---------------------------------------------------------------------------
# Lazy imports -- MCP SDK with OAuth support is optional
# ---------------------------------------------------------------------------

_OAUTH_AVAILABLE=False
try:
    from mcp.client.auth import OAuthClientProvider
    from mcp.shared.auth import (
        OAuthClientInformationFull,
        OAuthClientMetadata,
        OAuthMetadata,
        OAuthToken,
    )

    _OAUTH_AVAILABLE=True
except ImportError:
    logger.debug("MCP OAuth types not available -- OAuth MCP auth disabled")

try:
    from pydantic import AnyUrl
except ImportError:
    AnyUrl = None  # type: ignore[assignment, misc]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class OAuthNonInteractiveError(RuntimeError):
    """Raised when OAuth requires browser interaction in a non-interactive env."""


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

# Port used by the most recent build_oauth_auth() / MCPOAuthManager build.
# Exposed so that tests can verify the callback server and redirect_uri match.
_oauth_port: int | None = None

# Matches oauth.timeout in config (set in _configure_callback_port).
_oauth_callback_timeout: float = 300.0

# Held from a successful ``redirect_handler`` acquire until ``callback_handler`` finishes.
_oauth_flow_lock_acquired: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_oauth_flow_lock_acquired", default=False
)

# Monotonic timestamp of the last printed OAuth authorize URL (debounce logging).
_last_oauth_authorize_mono: float = 0.0


def _oauth_callback_wait_lock() -> asyncio.Lock:
    """Serialize localhost callback listeners on this event loop."""
    loop = asyncio.get_running_loop()
    key = id(loop)
    lock = _oauth_callback_wait_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _oauth_callback_wait_locks[key] = lock
    return lock


async def _oauth_begin_interactive_flow() -> None:
    """Acquire the per-loop lock before showing an OAuth URL (pairs with callback)."""
    await _oauth_callback_wait_lock().acquire()
    _oauth_flow_lock_acquired.set(True)


def _oauth_release_interactive_flow_if_held() -> None:
    if _oauth_flow_lock_acquired.get():
        _oauth_callback_wait_lock().release()
        _oauth_flow_lock_acquired.set(False)


def _get_token_dir() -> Path:
    """Return the directory for MCP OAuth token files.

    Uses HERMES_HOME so each profile gets its own OAuth tokens.
    Layout: ``HERMES_HOME/mcp-tokens/``
    """
    try:
        from hermes_constants import get_hermes_home
        base = Path(get_hermes_home())
    except ImportError:
        base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    return base / "mcp-tokens"


def _safe_filename(name: str) -> str:
    """Sanitize a server name for use as a filename (no path separators)."""
    return re.sub(r"[^\w\-]", "_", name).strip("_")[:128] or "default"


def _find_free_port() -> int:
    """Find an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _is_interactive() -> bool:
    """Return True if we can reasonably expect to interact with a user."""
    try:
        return sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def _can_open_browser() -> bool:
    """Return True if opening a browser is likely to work."""
    # Explicit SSH session → no local display
    if os.environ.get("SSH_CLIENT") or os.environ.get("SSH_TTY"):
        return False
    # macOS and Windows usually have a display
    if os.name == "nt":
        return True
    try:
        if os.uname().sysname == "Darwin":
            return True
    except AttributeError:
        pass
    # Linux/other posix: need DISPLAY or WAYLAND_DISPLAY
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return True
    return False


def _sync_access_remaining_seconds_from_disk_payload(
    data: dict, tokens_path: Path
) -> float | None:
    """Best-effort remaining access-token TTL from a persisted JSON payload."""
    absolute_expiry = data.get("expires_at")
    if absolute_expiry is not None:
        try:
            return float(absolute_expiry) - time.time()
        except (TypeError, ValueError):
            pass
    expires_in = data.get("expires_in")
    if expires_in is not None:
        try:
            file_mtime = tokens_path.stat().st_mtime
            implied_expiry = file_mtime + int(expires_in)
            return float(implied_expiry) - time.time()
        except (OSError, TypeError, ValueError):
            try:
                return float(int(expires_in))
            except (TypeError, ValueError):
                pass
    return None


def oauth_http_auth_feasible(server_name: str) -> bool:
    """Return whether HTTP MCP OAuth can run without blocking on a missing browser flow.

    If there are no tokens on disk, completing OAuth requires either a local browser
    (or a workstation-like environment) or an explicit opt-in for headless tunneling.

    Without this guard, ``discover_mcp_tools`` on a headless server with ``auth: oauth``
    and missing/invalid tokens would open the interactive redirect + callback wait and
    stall Hermes startup (Zapier, etc.).
    """
    if os.environ.get("HERMES_MCP_OAUTH_ALLOW_HEADLESS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return True
    storage = HermesTokenStorage(server_name)
    if storage.has_cached_tokens():
        if _can_open_browser():
            return True
        # SSH / CI: token files from an old laptop login are not enough — only
        # proceed if we likely won't need an interactive PKCE browser step.
        if storage.oauth_may_work_without_interactive_browser():
            return True
        logger.warning(
            "MCP server '%s': OAuth tokens on disk cannot be refreshed here "
            "(SSH/headless, expired access, or missing metadata). Skipping OAuth "
            "for this run — run `hermes mcp login %s` on a machine with a browser, "
            "copy mcp-tokens into this profile, set HERMES_MCP_OAUTH_ALLOW_HEADLESS=1 "
            "with a tunneled callback, or set mcp_servers.%s.enabled: false.",
            server_name,
            server_name,
            server_name,
        )
        return False
    return _can_open_browser()


def _read_json(path: Path) -> dict | None:
    """Read a JSON file, returning None if it doesn't exist or is invalid."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return None


def _write_json(path: Path, data: dict) -> None:
    """Write a dict as JSON with restricted permissions (0o600).

    Uses ``os.open`` with ``O_EXCL`` and an explicit mode so the file is
    created atomically at 0o600. The previous ``write_text`` + post-write
    ``chmod`` opened a TOCTOU window where the temp file briefly inherited
    the process umask (commonly 0o644 = world-readable), exposing OAuth
    tokens to other local users between create and chmod. Mirrors the fix
    in ``agent/google_oauth.py`` (#19673).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Tighten parent dir to 0o700 so siblings can't traverse to the creds.
    # No-op on Windows (POSIX mode bits aren't enforced); ignore failures.
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    # Per-process random suffix avoids collisions between concurrent
    # writers and stale leftovers from a prior crashed write.
    tmp = path.with_suffix(f".tmp.{os.getpid()}.{secrets.token_hex(4)}")
    try:
        fd = os.open(
            str(tmp),
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            stat.S_IRUSR | stat.S_IWUSR,
        )
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=str)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# HermesTokenStorage -- persistent token/client-info on disk
# ---------------------------------------------------------------------------


class HermesTokenStorage:
    """Persist OAuth tokens and client registration to JSON files.

    File layout::

        HERMES_HOME/mcp-tokens/<server_name>.json         -- tokens
        HERMES_HOME/mcp-tokens/<server_name>.client.json   -- client info
        HERMES_HOME/mcp-tokens/<server_name>.meta.json     -- oauth server metadata
    """

    def __init__(self, server_name: str):
        self._server_name = _safe_filename(server_name)

    def _tokens_path(self) -> Path:
        return _get_token_dir() / f"{self._server_name}.json"

    def _client_info_path(self) -> Path:
        return _get_token_dir() / f"{self._server_name}.client.json"

    def _meta_path(self) -> Path:
        return _get_token_dir() / f"{self._server_name}.meta.json"

    # -- tokens ------------------------------------------------------------

    async def get_tokens(self) -> "OAuthToken | None":
        data = _read_json(self._tokens_path())
        if data is None:
            return None
        # Hermes records an absolute wall-clock ``expires_at`` alongside the
        # SDK's serialized token (see ``set_tokens``). On read we rewrite
        # ``expires_in`` to the remaining seconds so the SDK's downstream
        # ``update_token_expiry`` computes the correct absolute time and
        # ``is_token_valid()`` correctly reports False for tokens that
        # expired while the process was down.
        #
        # Legacy token files (pre-Fix-A) have ``expires_in`` but no
        # ``expires_at``. We fall back to the file's mtime as a best-effort
        # wall-clock proxy for when the token was written: if (mtime +
        # expires_in) is in the past, clamp ``expires_in`` to zero so the
        # SDK refreshes before the first request. This self-heals one-time
        # on the next successful ``set_tokens``, which writes the new
        # ``expires_at`` field. The stored ``expires_at`` is stripped before
        # model_validate because it's not part of the SDK's OAuthToken schema.
        absolute_expiry = data.pop("expires_at", None)
        if absolute_expiry is not None:
            data["expires_in"] = int(max(absolute_expiry - time.time(), 0))
        elif data.get("expires_in") is not None:
            try:
                file_mtime = self._tokens_path().stat().st_mtime
            except OSError:
                file_mtime = None
            if file_mtime is not None:
                try:
                    implied_expiry = file_mtime + int(data["expires_in"])
                    data["expires_in"] = int(max(implied_expiry - time.time(), 0))
                except (TypeError, ValueError):
                    pass
        try:
            return OAuthToken.model_validate(data)
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning("Corrupt tokens at %s -- ignoring: %s", self._tokens_path(), exc)
            return None

    async def set_tokens(self, tokens: "OAuthToken") -> None:
        payload = tokens.model_dump(mode="json", exclude_none=True)
        # Persist an absolute ``expires_at`` so a process restart can
        # reconstruct the correct remaining TTL. Without this the MCP SDK's
        # ``_initialize`` reloads a relative ``expires_in`` which has no
        # wall-clock reference, leaving ``context.token_expiry_time=None``
        # and ``is_token_valid()`` falsely reporting True. See Fix A in
        # ``mcp-oauth-token-diagnosis`` skill + Claude Code's
        # ``OAuthTokens.expiresAt`` persistence (auth.ts ~180).
        expires_in = payload.get("expires_in")
        if expires_in is not None:
            try:
                payload["expires_at"] = time.time() + int(expires_in)
            except (TypeError, ValueError):
                # Mock tokens or unusual shapes: skip the expires_at write
                # rather than fail persistence.
                pass
        _write_json(self._tokens_path(), payload)
        logger.debug("OAuth tokens saved for %s", self._server_name)

    # -- client info -------------------------------------------------------

    async def get_client_info(self) -> "OAuthClientInformationFull | None":
        data = _read_json(self._client_info_path())
        if data is None:
            return None
        try:
            return OAuthClientInformationFull.model_validate(data)
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning("Corrupt client info at %s -- ignoring: %s", self._client_info_path(), exc)
            return None

    async def set_client_info(self, client_info: "OAuthClientInformationFull") -> None:
        _write_json(self._client_info_path(), client_info.model_dump(mode="json", exclude_none=True))
        logger.debug("OAuth client info saved for %s", self._server_name)

    # -- oauth server metadata --------------------------------------------
    # The MCP SDK keeps discovered ``OAuthMetadata`` (token endpoint URL,
    # etc.) in memory only. Persisting it here lets a restarted process
    # refresh tokens without re-running metadata discovery. Without this,
    # cold-start refresh requests fall back to the SDK's guessed
    # ``{server_url}/token`` which returns 404 on most real providers and
    # forces a full browser re-authorization.

    def save_oauth_metadata(self, metadata: "OAuthMetadata") -> None:
        _write_json(self._meta_path(), metadata.model_dump(exclude_none=True, mode="json"))
        logger.debug("OAuth metadata saved for %s", self._server_name)

    def load_oauth_metadata(self) -> "OAuthMetadata | None":
        data = _read_json(self._meta_path())
        if data is None:
            return None
        try:
            return OAuthMetadata.model_validate(data)
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning("Corrupt OAuth metadata at %s -- ignoring: %s", self._meta_path(), exc)
            return None

    # -- cleanup -----------------------------------------------------------

    def remove(self) -> None:
        """Delete all stored OAuth state for this server."""
        for p in (self._tokens_path(), self._client_info_path(), self._meta_path()):
            p.unlink(missing_ok=True)

    def has_cached_tokens(self) -> bool:
        """Return True if we have tokens on disk (may be expired)."""
        return self._tokens_path().exists()

    def oauth_may_work_without_interactive_browser(self) -> bool:
        """Whether disk OAuth state can plausibly succeed without a local browser.

        Used on SSH/headless hosts: a token *file* existing is not enough — stale
        access tokens would otherwise drive PKCE browser auth and block ``hermes
        chat`` startup (Zapier, etc.).  We only return True when the access token
        still has comfortable TTL or we have refresh + persisted OAuth metadata
        (token endpoint) so a silent refresh can run.
        """
        data = _read_json(self._tokens_path())
        if not data or not isinstance(data, dict):
            return False
        remaining = _sync_access_remaining_seconds_from_disk_payload(
            data, self._tokens_path()
        )
        if remaining is not None and remaining > 120:
            return True
        if not data.get("refresh_token"):
            return False
        return self.load_oauth_metadata() is not None


# ---------------------------------------------------------------------------
# Callback handler factory -- each invocation gets its own result dict
# ---------------------------------------------------------------------------


class _OAuthCallbackHTTPServer(HTTPServer):
    """Callback listener with SO_REUSEADDR for rapid OAuth retries on macOS."""

    allow_reuse_address = True


def _make_callback_handler() -> tuple[type, dict]:
    """Create a per-flow callback HTTP handler class with its own result dict.

    Returns ``(HandlerClass, result_dict)`` where *result_dict* is a mutable
    dict that the handler writes ``auth_code`` and ``state`` into when the
    OAuth redirect arrives.  Each call returns a fresh pair so concurrent
    flows don't stomp on each other.
    """
    result: dict[str, Any] = {"auth_code": None, "state": None, "error": None}

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            params = parse_qs(urlparse(self.path).query)
            code = params.get("code", [None])[0]
            state = params.get("state", [None])[0]
            error = params.get("error", [None])[0]

            result["auth_code"] = code
            result["state"] = state
            result["error"] = error

            logger.info(
                "MCP OAuth /callback received (code_present=%s error=%s)",
                bool(code),
                error or "",
            )

            body = (
                "<html><body><h2>Authorization Successful</h2>"
                "<p>You can close this tab and return to Hermes.</p></body></html>"
            ) if code else (
                "<html><body><h2>Authorization Failed</h2>"
                f"<p>Error: {error or 'unknown'}</p></body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())

        def log_message(self, fmt: str, *args: Any) -> None:
            logger.debug("OAuth callback: %s", fmt % args)

    return _Handler, result


# ---------------------------------------------------------------------------
# Async redirect + callback handlers for OAuthClientProvider
# ---------------------------------------------------------------------------


def _oauth_wants_auto_open_browser(oauth_cfg: dict) -> bool:
    """Whether to call :func:`webbrowser.open` after printing the authorize URL."""
    if os.environ.get("HERMES_MCP_OAUTH_NO_BROWSER", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return False
    if oauth_cfg.get("open_browser") is False:
        return False
    return True


async def _emit_mcp_oauth_authorization_url(
    authorization_url: str,
    *,
    open_browser: bool,
    callback_port: int | None = None,
) -> None:
    """Print the authorize URL; optionally open the system browser."""
    global _last_oauth_authorize_mono
    allow_headless = os.environ.get("HERMES_MCP_OAUTH_ALLOW_HEADLESS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    # Never dump a Zapier-length authorize URL on SSH/headless unless the
    # operator opted in — token refresh may still fall back to full PKCE here
    # even when :func:`oauth_http_auth_feasible` was optimistic.
    if not _can_open_browser() and not allow_headless:
        raise OAuthNonInteractiveError(
            "MCP OAuth needs a local browser (or set HERMES_MCP_OAUTH_ALLOW_HEADLESS=1 "
            "if you will tunnel http://127.0.0.1:<port>/callback). "
            "Run `hermes mcp login <server>` on a machine with a display, copy "
            "$HERMES_HOME/mcp-tokens/, or set mcp_servers.<name>.enabled: false."
        )

    now = time.monotonic()
    if _last_oauth_authorize_mono > 0.0 and (now - _last_oauth_authorize_mono) < 45.0:
        gap = now - _last_oauth_authorize_mono
        logger.warning(
            "MCP OAuth: second authorization prompt within %.1fs — a prior flow "
            "may have failed before tokens were saved. Use only the newest URL and "
            "close older browser tabs (state/PKCE must match this run).",
            gap,
        )
        print(
            "\n  Warning: Hermes printed another OAuth link while a recent flow is "
            "still in progress. Use ONLY the URL below (newest) so state matches.\n",
            file=sys.stderr,
        )
    _last_oauth_authorize_mono = now

    msg = (
        f"\n  MCP OAuth: authorization required.\n"
        f"  Open this URL in your browser (single tab):\n\n"
        f"    {authorization_url}\n"
    )
    print(msg, file=sys.stderr)
    if callback_port is not None:
        print(
            f"  After you approve, the provider must redirect your browser to "
            f"http://127.0.0.1:{callback_port}/callback on the same machine "
            f"that is running Hermes.\n"
            f"  If you use SSH or another PC, tunnel or run login locally and copy "
            "tokens — 127.0.0.1 here always means this host, not your laptop.\n",
            file=sys.stderr,
        )
    if not open_browser:
        print(
            "  (Automatic browser open disabled — use the printed URL once.)\n",
            file=sys.stderr,
        )
        return

    if _can_open_browser():
        try:
            opened = webbrowser.open(authorization_url)
            if opened:
                print("  (Browser opened automatically.)\n", file=sys.stderr)
            else:
                print("  (Could not open browser — please open the URL manually.)\n", file=sys.stderr)
        except Exception:
            print("  (Could not open browser — please open the URL manually.)\n", file=sys.stderr)
    else:
        print("  (Headless environment detected — open the URL manually.)\n", file=sys.stderr)


def make_redirect_handler(oauth_cfg: dict) -> Any:
    """Build a redirect handler that respects ``oauth.open_browser`` in config.

    Call after :func:`_configure_callback_port` so ``oauth_cfg['_resolved_port']``
    is set (used for user-facing callback guidance).
    """
    port = oauth_cfg.get("_resolved_port")

    async def _handler(authorization_url: str) -> None:
        await _emit_mcp_oauth_authorization_url(
            authorization_url,
            open_browser=_oauth_wants_auto_open_browser(oauth_cfg),
            callback_port=port if isinstance(port, int) else None,
        )

    return _handler


async def _redirect_handler(authorization_url: str) -> None:
    """Legacy entrypoint — prefer :func:`make_redirect_handler` with server config."""
    await _emit_mcp_oauth_authorization_url(
        authorization_url,
        open_browser=_oauth_wants_auto_open_browser({}),
        callback_port=_oauth_port,
    )


def _make_paired_oauth_handlers(oauth_cfg: dict) -> tuple[Any, Any]:
    """Redirect + callback handlers that share one asyncio lock per OAuth attempt.

    Prevents a second MCP OAuth round (retry 401, parallel httpx, etc.) from
    printing another authorize URL or binding ``redirect_port`` while the first
    browser round-trip is still in progress.
    """
    port = oauth_cfg.get("_resolved_port")

    async def _paired_redirect(authorization_url: str) -> None:
        await _oauth_begin_interactive_flow()
        try:
            await _emit_mcp_oauth_authorization_url(
                authorization_url,
                open_browser=_oauth_wants_auto_open_browser(oauth_cfg),
                callback_port=port if isinstance(port, int) else None,
            )
        except BaseException:
            _oauth_release_interactive_flow_if_held()
            raise

    async def _paired_callback() -> tuple[str, str | None]:
        try:
            return await _oauth_callback_listen_impl()
        finally:
            _oauth_release_interactive_flow_if_held()

    return _paired_redirect, _paired_callback


async def _oauth_callback_listen_impl() -> tuple[str, str | None]:
    """Wait for the OAuth callback to arrive on the local callback server.

    Uses the module-level ``_oauth_port`` which is set by ``build_oauth_auth``
    before this is ever called.  Polls for the result without blocking the
    event loop.

    Raises:
        OAuthNonInteractiveError: If the callback times out (no user present
            to complete the browser auth).
        RuntimeError: If ``_oauth_port`` has not been set, which would indicate
            that ``build_oauth_auth`` was skipped — the asserting form below
            was a silent bug when running Python with ``-O``/``-OO``.
    """
    if _oauth_port is None:
        raise RuntimeError(
            "OAuth callback port not set — build_oauth_auth must be called "
            "before _wait_for_oauth_callback"
        )

    handler_cls, result = _make_callback_handler()

    callback_url = f"http://127.0.0.1:{_oauth_port}/callback"
    logger.info("MCP OAuth waiting for redirect to %s", callback_url)
    print(
        f"  Listening for OAuth redirect on {callback_url}\n",
        file=sys.stderr,
    )

    try:
        server = _OAuthCallbackHTTPServer(("127.0.0.1", _oauth_port), handler_cls)
    except OSError as exc:
        raise OAuthNonInteractiveError(
            f"OAuth callback cannot listen on {callback_url} ({exc}). "
            "Another process may be using this port — pick a different "
            "mcp_servers.<name>.oauth.redirect_port, stop the other process, "
            "or ensure only one Hermes OAuth login runs at a time."
        ) from exc

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    timeout = float(_oauth_callback_timeout)
    poll_interval = 0.5
    elapsed = 0.0
    try:
        while elapsed < timeout:
            if result["auth_code"] is not None or result["error"] is not None:
                break
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
    finally:
        try:
            server.shutdown()
        except Exception:
            logger.debug("OAuth callback server shutdown failed", exc_info=True)
        server_thread.join(timeout=5.0)
        if server_thread.is_alive():
            logger.warning(
                "MCP OAuth callback server thread did not stop within 5s "
                "(redirect_port=%s may remain busy briefly)",
                _oauth_port,
            )
        try:
            server.server_close()
        except Exception:
            logger.debug("OAuth callback server_close failed", exc_info=True)

    if result["error"]:
        raise RuntimeError(f"OAuth authorization failed: {result['error']}")
    if result["auth_code"] is None:
        raise OAuthNonInteractiveError(
            "OAuth callback timed out — no authorization code received. "
            "Ensure you completed the browser authorization flow."
        )

    return result["auth_code"], result["state"]


async def _wait_for_callback() -> tuple[str, str | None]:
    """Callback-only entry (tests). Production uses paired handlers from
    :func:`_make_paired_oauth_handlers`.
    """
    return await _oauth_callback_listen_impl()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def remove_oauth_tokens(server_name: str) -> None:
    """Delete stored OAuth tokens and client info for a server."""
    storage = HermesTokenStorage(server_name)
    storage.remove()
    logger.info("OAuth tokens removed for '%s'", server_name)


# ---------------------------------------------------------------------------
# Extracted helpers (Task 3 of MCP OAuth consolidation)
#
# These compose into ``build_oauth_auth`` below, and are also used by
# ``tools.mcp_oauth_manager.MCPOAuthManager._build_provider`` so the two
# construction paths share one implementation.
# ---------------------------------------------------------------------------


def _configure_callback_port(cfg: dict) -> int:
    """Pick or validate the OAuth callback port.

    Stores the resolved port into ``cfg['_resolved_port']`` so sibling
    helpers (and the manager) can read it from the same dict. Returns the
    resolved port.

    NOTE: also sets the legacy module-level ``_oauth_port`` so existing
    calls to ``_wait_for_callback`` keep working. The legacy global is
    the root cause of issue #5344 (port collision on concurrent OAuth
    flows); replacing it with a ContextVar is out of scope for this
    consolidation PR.
    """
    global _oauth_port, _oauth_callback_timeout
    requested = int(cfg.get("redirect_port", 0))
    port = _find_free_port() if requested == 0 else requested
    cfg["_resolved_port"] = port
    _oauth_port = port  # legacy consumer: _wait_for_callback reads this
    _oauth_callback_timeout = float(cfg.get("timeout", 300))
    return port


def _build_client_metadata(cfg: dict) -> "OAuthClientMetadata":
    """Build OAuthClientMetadata from the oauth config dict.

    Requires ``cfg['_resolved_port']`` to have been populated by
    :func:`_configure_callback_port` first.
    """
    port = cfg.get("_resolved_port")
    if port is None:
        raise ValueError(
            "_configure_callback_port() must be called before _build_client_metadata()"
        )
    client_name = cfg.get("client_name", "Hermes Agent")
    scope = cfg.get("scope")
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    metadata_kwargs: dict[str, Any] = {
        "client_name": client_name,
        "redirect_uris": [AnyUrl(redirect_uri)],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    if scope:
        metadata_kwargs["scope"] = scope
    if cfg.get("client_secret"):
        metadata_kwargs["token_endpoint_auth_method"] = "client_secret_post"

    return OAuthClientMetadata.model_validate(metadata_kwargs)


def _maybe_preregister_client(
    storage: "HermesTokenStorage",
    cfg: dict,
    client_metadata: "OAuthClientMetadata",
) -> None:
    """If cfg has a pre-registered client_id, persist it to storage."""
    client_id = cfg.get("client_id")
    if not client_id:
        return
    port = cfg["_resolved_port"]
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    info_dict: dict[str, Any] = {
        "client_id": client_id,
        "redirect_uris": [redirect_uri],
        "grant_types": client_metadata.grant_types,
        "response_types": client_metadata.response_types,
        "token_endpoint_auth_method": client_metadata.token_endpoint_auth_method,
    }
    if cfg.get("client_secret"):
        info_dict["client_secret"] = cfg["client_secret"]
    if cfg.get("client_name"):
        info_dict["client_name"] = cfg["client_name"]
    if cfg.get("scope"):
        info_dict["scope"] = cfg["scope"]

    client_info = OAuthClientInformationFull.model_validate(info_dict)
    _write_json(storage._client_info_path(), client_info.model_dump(mode="json", exclude_none=True))
    logger.debug("Pre-registered client_id=%s for '%s'", client_id, storage._server_name)


def build_oauth_auth(
    server_name: str,
    server_url: str,
    oauth_config: dict | None = None,
) -> "OAuthClientProvider | None":
    """Build an ``httpx.Auth``-compatible OAuth handler for an MCP server.

    Public API preserved for backwards compatibility. New code should use
    :func:`tools.mcp_oauth_manager.get_manager` so OAuth state is shared
    across config-time, runtime, and reconnect paths.

    Args:
        server_name: Server key in mcp_servers config (used for storage).
        server_url: MCP server endpoint URL.
        oauth_config: Optional dict from the ``oauth:`` block in config.yaml.

    Returns:
        An ``OAuthClientProvider`` instance, or None if the MCP SDK lacks
        OAuth support.
    """
    if not _OAUTH_AVAILABLE:
        logger.warning(
            "MCP OAuth requested for '%s' but SDK auth types are not available. "
            "Install with: pip install 'mcp>=1.26.0'",
            server_name,
        )
        return None

    cfg = dict(oauth_config or {})  # copy — we mutate _resolved_port
    storage = HermesTokenStorage(server_name)

    if not _is_interactive() and not storage.has_cached_tokens():
        logger.warning(
            "MCP OAuth for '%s': non-interactive environment and no cached tokens "
            "found. The OAuth flow requires browser authorization. Run "
            "interactively first to complete the initial authorization, then "
            "cached tokens will be reused.",
            server_name,
        )

    _configure_callback_port(cfg)
    client_metadata = _build_client_metadata(cfg)
    _maybe_preregister_client(storage, cfg, client_metadata)

    redirect_h, callback_h = _make_paired_oauth_handlers(cfg)
    return OAuthClientProvider(
        server_url=server_url,
        client_metadata=client_metadata,
        storage=storage,
        redirect_handler=redirect_h,
        callback_handler=callback_h,
        timeout=float(cfg.get("timeout", 300)),
    )
