# Changelog

## Unreleased

- Paperclip: when the built-in `/paperclip` command is present, Paperclip bridge skills no longer register a second `slash_commands` / TUI catalog entry (e.g. `/paperclip-dot-hermes-bridge`). TUI `commands.catalog` also skips `quick_commands` that collide with registry slash names.
- Autoresearch: gateway `/autoresearch` engagement uses Hermes `session_id` (not the stable per-channel key), and the agent prefers `session_id` for scope matching — fixes outer wall-clock arming on every new session in the same DM.
- Linux VPS: documented systemd gateway install with `--run-as-user` so `User=` matches `HERMES_HOME` (avoid root-owned locks); see `docs/hermes-runtime-architecture.md`.
- Added handover v4 configuration defaults for adaptive routing, emergency fallback, spend governance, profile routing, organization escalation, delegation policy, Kanban orchestration, and runtime footer fields. All new features are disabled by default.
- Added adaptive routing, emergency fallback status, and spend governance runtime hooks with profile-local persistence under `HERMES_HOME`.
- Added ephemeral profile creation via `hermes profile create --ephemeral`.
