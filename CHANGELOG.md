# Changelog

## Unreleased

- Linux VPS: documented systemd gateway install with `--run-as-user` so `User=` matches `HERMES_HOME` (avoid root-owned locks); see `docs/hermes-runtime-architecture.md`.
- Added handover v4 configuration defaults for adaptive routing, emergency fallback, spend governance, profile routing, organization escalation, delegation policy, Kanban orchestration, and runtime footer fields. All new features are disabled by default.
- Added adaptive routing, emergency fallback status, and spend governance runtime hooks with profile-local persistence under `HERMES_HOME`.
- Added ephemeral profile creation via `hermes profile create --ephemeral`.
