# Changelog

## Unreleased

- Fixed `ImportError` for `TERMINAL_OUTPUT_GUIDANCE` — `run_agent` imported it but `prompt_builder` did not define it on `main`.
- MCP: OAuth providers no longer print a giant browser URL on SSH/headless unless `HERMES_MCP_OAUTH_ALLOW_HEADLESS=1` — the flow aborts with `OAuthNonInteractiveError` so `hermes chat` and plugin commands can start; use `hermes mcp login`, sync `mcp-tokens/`, or disable the server.
- MCP: over SSH / headless, a Zapier (or other OAuth) token file no longer triggers an interactive browser PKCE flow unless the access token still has TTL or refresh + OAuth metadata can run silently — stale bare `access_token` files skip OAuth so `hermes chat` and similar commands start normally.
- Paperclip: when the built-in `/paperclip` command is present, Paperclip bridge skills no longer register a second `slash_commands` / TUI catalog entry (e.g. `/paperclip-dot-hermes-bridge`). TUI `commands.catalog` also skips `quick_commands` that collide with registry slash names.
- Paperclip: vendored patched `hermes-paperclip-adapter` (0.3.1) under `contrib/hermes-paperclip-adapter` — resolves the CLI via `python3 -m hermes_cli.main` when the `hermes` shim is missing from the Paperclip server PATH (adapter env check + runs). See `contrib/hermes-paperclip-adapter/README.md` and `skills/devops/paperclip-dot-hermes-bridge/SKILL.md`.
- Paperclip: ``/pc`` is no longer a second Slack slash or CLI autocomplete row alongside ``/paperclip``; typing ``/pc`` and ``/hermes pc`` still resolve to the same handler.
- Paperclip: gateway and CLI implement ``/paperclip`` / ``/pc`` via ``tools.paperclip_slash`` (links + optional local browser open); ``paperclip_env`` centralizes URL env vars.
- Autoresearch: gateway `/autoresearch` engagement uses Hermes `session_id` (not the stable per-channel key), and the agent prefers `session_id` for scope matching — fixes outer wall-clock arming on every new session in the same DM.
- Linux VPS: documented systemd gateway install with `--run-as-user` so `User=` matches `HERMES_HOME` (avoid root-owned locks); see `docs/hermes-runtime-architecture.md`.
- Added handover v4 configuration defaults for adaptive routing, emergency fallback, spend governance, profile routing, organization escalation, delegation policy, Kanban orchestration, and runtime footer fields. All new features are disabled by default.
- Added adaptive routing, emergency fallback status, and spend governance runtime hooks with profile-local persistence under `HERMES_HOME`.
- Added ephemeral profile creation via `hermes profile create --ephemeral`.
