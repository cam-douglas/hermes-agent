# Operations — runtime registers and project memory

This directory holds **operational truth** for a deployed agentic company: org registers, security queues, incidents, and **per-project** memory trees.

It is **not** a copy of `policies/` and not a general-purpose notes folder.

## Layout

See `policies/core/governance/artifacts-and-archival-memory.md` for the full tree.

Minimum files (create empty stubs with defined templates if missing):

- `ORG_REGISTRY.md`
- `ORG_CHART.md`
- `AGENT_LIFECYCLE_REGISTER.md`
- `TASK_STATE_STANDARD.md`
- `BOARD_REVIEW_REGISTER.md`
- `CHANNEL_ARCHITECTURE.md`
- `SECURITY_ALERT_REGISTER.md`
- `SECURITY_AUDIT_REPORT.md`
- `SECURITY_REMEDIATION_QUEUE.md`
- `INCIDENT_REGISTER.md`

Per project:

- `projects/<project_slug>/README.md`
- `projects/<project_slug>/memory/archival/` — **append-only** recall-oriented files
- `projects/<project_slug>/artifacts/` — outputs
- `projects/<project_slug>/generated/` — project-only markdown (indexed in project README)

## Access

Orchestrator and project leads have visibility per canonical pack. Workers see only their project subtree unless escalated.
