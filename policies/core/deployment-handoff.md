<!-- policy-read-order-nav:top -->
> **Governance read order** — step 3 of 53 in the canonical `policies/` sequence (layer map & tables: [`README.md`](../README.md)).
> **Before this file:** read [core/unified-deployment-and-security.md](unified-deployment-and-security.md) and everything earlier in that sequence. **Do not** interpret this document as authoritative until those prerequisites are satisfied.
> **This file:** safe to apply only after the prerequisite above (if any) is complete.
<!-- policy-read-order-nav:top-end -->

<!--
  read-order: 3 — Read after core/security-first-setup.md (1) and
  core/unified-deployment-and-security.md (2). Then run the pipeline script.
-->
# Deployment handoff

## Purpose

This is the **third** core handoff file: the builder/runtime handoff **after** both runbooks in [`core/`](README.md).

**Scope:** Deployment of an **agentic company** (governed multi-agent org, registers, archival memory). Not for configuring a default single-user assistant.

**Prerequisite reads (in order):**

1. [`security-first-setup.md`](security-first-setup.md)
2. [`unified-deployment-and-security.md`](unified-deployment-and-security.md)

This file exists to drive the full deployment process across:
- the canonical policies
- the canonical prompts
- the canonical runbooks
- the operational record files
- the bootstrap file
- the attached agent markdown files

The deployment process must treat this file as the start of the builder/runtime handoff.

---

## Required Order of Operations

Use this order:

1. `policies/core/security-first-setup.md`
2. `policies/core/unified-deployment-and-security.md`
3. `policies/core/deployment-handoff.md` (this file)
4. `python policies/core/scripts/start_pipeline.py` (or `./policies/start_pipeline.sh`) — verify tree, strict `standards/` cues, refresh `INDEX.md`; see [`pipeline-runbook.md`](pipeline-runbook.md)
5. `policies/core/runtime/agent/BOOTSTRAP.md`
6. `policies/core/runtime/agent/AGENTS.md`
7. the remaining attached agent markdown files referenced by `BOOTSTRAP.md` and `AGENTS.md` (paths under `policies/core/runtime/agent/` in this repository)

Do not skip `BOOTSTRAP.md`. It is required because it instigates and explains use of the full agent markdown pack.

---

## Builder / Deployer Prompt

```text
Review the existing workspace and deploy against the current policy structure rather than rebuilding the architecture from scratch.

The authoritative files already exist. Preserve the current `policies/` hierarchy unless a change is required for operational compatibility.

Authoritative entrypoints:
- `policies/README.md`
- `policies/core/governance/artifacts-and-archival-memory.md`
- `policies/core/agentic-company-deployment-pack.md`
- `policies/core/unified-deployment-and-security.md`

Primary prompt files:
- `policies/core/security-prompts.md`
- `policies/core/chief-orchestrator-directive.md`

Supporting policy and template sources:
- `policies/core/governance/standards/canonical-ai-agent-security-policy.md`
- `policies/core/governance/standards/org-mapper-hr-policy.md`
- `policies/core/governance/standards/functional-director-policy-template.md`
- `policies/core/governance/standards/project-lead-policy-template.md`
- `policies/core/governance/standards/supervisor-policy-template.md`
- `policies/core/governance/standards/worker-specialist-policy-template.md`
- `policies/core/governance/standards/board-of-directors-review-policy.md`
- `policies/core/governance/standards/task-state-and-evidence-policy.md`
- `policies/core/governance/standards/channel-architecture-policy.md`
- `policies/core/governance/standards/client-deployment-policy.md`
- `policies/core/governance/standards/agent-lifecycle-org-hygiene-policy.md`
- `policies/core/governance/standards/agentic-company-template.md`
- `policies/core/governance/role-prompts/org-mapper-hr-controller.md`
- `policies/core/governance/role-prompts/functional-director-template.md`
- `policies/core/governance/role-prompts/project-lead-template.md`
- `policies/core/governance/role-prompts/supervisor-template.md`
- `policies/core/governance/role-prompts/worker-specialist-template.md`
- `policies/core/governance/role-prompts/board-of-directors-review.md`
- `policies/core/governance/role-prompts/client-intake-deployment-template.md`
- `policies/core/governance/role-prompts/markdown-playbook-generator.md`
- `policies/core/governance/role-prompts/future-channel-architecture-planner.md`
- `policies/core/governance/role-prompts/agent-lifecycle-org-hygiene-controller.md`
- `policies/core/governance/role-prompts/task-state-evidence-enforcer.md`
- `policies/core/governance/role-prompts/minimal-default-deployment-order.md`

Attached agent markdown files that must be included in the full deployment process (under `policies/core/runtime/agent/` in this repo):
- `BOOTSTRAP.md`
- `AGENTS.md`
- `IDENTITY.md`
- `USER.md`
- `SOUL.md`
- `MEMORY.md`
- `ORCHESTRATOR.md`
- `RATE_LIMIT_POLICY.md`
- `TOOLS.md`
- `HEARTBEAT.md`
- `SECURITY.md`
- `README.md`

Deployment requirements for the agent markdown files:
1. verify that each attached agent markdown file exists
2. preserve them as part of the deployed operating environment
3. update them if needed so they correctly reference:
   - `policies/README.md` and `policies/core/governance/artifacts-and-archival-memory.md`
   - the canonical deployment pack
   - the unified runbook
   - this deployment-handoff file
   - the bootstrap process
4. ensure `BOOTSTRAP.md` becomes the bootstrapping handoff file for the agent markdown pack
5. ensure `BOOTSTRAP.md` clearly instructs the user/operator/runtime how to use the other attached agent markdown files
6. ensure `AGENTS.md` clearly defines the startup/read order and references the canonical deployment flow
7. ensure the other agent markdown files are treated as subordinate operating files under the bootstrap process
8. ensure orchestrator and project-facing files encode **continuous archival memory** and **generated markdown** rules from `policies/core/governance/artifacts-and-archival-memory.md`

Your role is builder and file-level deployer, not policy author. Do not redesign the architecture unless a contradiction prevents implementation.

Tasks:
1. Verify the `policies/` tree exists and is readable.
2. Treat `policies/core/agentic-company-deployment-pack.md` as the canonical entrypoint.
3. Treat `policies/core/unified-deployment-and-security.md` as the canonical operational runbook.
4. Treat the two files in `policies/core/` as the primary activation prompt sources.
5. Preserve the current folder layout unless a runtime compatibility issue requires change.
6. Verify the attached agent markdown pack exists and is readable.
7. Use `policies/core/runtime/agent/BOOTSTRAP.md` as the bootstrapping file for the agent markdown pack.
8. Ensure `BOOTSTRAP.md` instigates and explains deployment/use of the other attached agent markdown files.
9. Ensure `AGENTS.md` and the other attached agent markdown files contain references to the canonical policies, prompts, runbook, artifact pipeline, and bootstrap flow where relevant.
10. Create or initialize the operational files required by the runbook if they do not already exist, under `operations/` (see `operations/README.md`):
   - `operations/ORG_REGISTRY.md`
   - `operations/ORG_CHART.md`
   - `operations/AGENT_LIFECYCLE_REGISTER.md`
   - `operations/TASK_STATE_STANDARD.md`
   - `operations/BOARD_REVIEW_REGISTER.md`
   - `operations/CHANNEL_ARCHITECTURE.md`
   - `operations/SECURITY_ALERT_REGISTER.md`
   - `operations/SECURITY_AUDIT_REPORT.md`
   - `operations/SECURITY_REMEDIATION_QUEUE.md`
   - `operations/INCIDENT_REGISTER.md`
11. Create `operations/projects/` and ensure per-project `memory/archival/` trees exist for every active project slug.
12. Initialize `policies/core/governance/generated/README.md` and subfolders per `policies/core/governance/artifacts-and-archival-memory.md`; keep the index updated whenever new generated markdown is added.
13. Create any supporting folders, registries, templates, and operational files required by the runbook, but do not clone or duplicate the canonical policy documents unnecessarily.
14. Do not activate agents yourself unless explicitly required by runtime design.
15. Do not weaken any security or governance rule for convenience.
16. If there is ambiguity, choose the leanest, most auditable implementation consistent with the current canonical pack.

Output a concise deployment summary showing:
- policy files verified
- prompt files verified
- agent markdown files verified
- agent markdown files modified or initialized
- operational files created
- directories created
- unresolved ambiguities
- anything intentionally left for runtime activation
```

---

## Runtime Activation Prompt

```text
The deployment files, policies, prompts, registries, runbooks, and agent markdown files already exist in this workspace.

Your role is not to redesign the system. Your role is to activate, validate, and operate the deployed architecture in strict compliance with the existing canonical pack, runbook, bootstrap file, and agent markdown pack.

Use this exact load order:

1. `policies/core/security-first-setup.md`
2. `policies/core/unified-deployment-and-security.md`
3. `policies/core/deployment-handoff.md` (this document)
4. `python policies/core/scripts/start_pipeline.py` — see `policies/core/pipeline-runbook.md`
5. `policies/README.md`
6. `policies/README.md`
7. `policies/core/governance/artifacts-and-archival-memory.md`
8. `policies/core/agentic-company-deployment-pack.md`
9. `policies/core/security-prompts.md`
10. `policies/core/chief-orchestrator-directive.md`
11. `policies/core/runtime/agent/BOOTSTRAP.md`
12. `policies/core/runtime/agent/AGENTS.md`
13. the remaining attached agent markdown files (under `policies/core/runtime/agent/` in this repository):
   - `policies/core/runtime/agent/IDENTITY.md`
   - `policies/core/runtime/agent/USER.md`
   - `policies/core/runtime/agent/SOUL.md`
   - `policies/core/runtime/agent/MEMORY.md`
   - `policies/core/runtime/agent/ORCHESTRATOR.md`
   - `policies/core/runtime/agent/RATE_LIMIT_POLICY.md`
   - `policies/core/runtime/agent/TOOLS.md`
   - `policies/core/runtime/agent/HEARTBEAT.md`
   - `policies/core/runtime/agent/SECURITY.md`
   - `policies/core/runtime/agent/README.md`
14. secondary supporting policy files in `policies/core/governance/standards/`
15. secondary supporting role templates in `policies/core/governance/role-prompts/`
16. `operations/` registers and `operations/projects/*/memory/archival/` as applicable
17. `policies/core/governance/generated/` index and governed additions

Activation rules:
1. Treat the canonical deployment pack as authoritative.
2. Treat the unified deployment/security runbook as the operational procedure.
3. Treat `policies/core/runtime/agent/BOOTSTRAP.md` as the bootstrap handoff file for the agent markdown pack.
4. Treat `policies/core/runtime/agent/AGENTS.md` as the startup/read-order and workspace agent rules file.
5. Do not create ad hoc structure outside the canonical framework unless runtime operation strictly requires it.
6. Do not duplicate or rename policy files unless necessary for compatibility.
7. Do not activate broad execution or project work until the security foundation is active.

Before broader activation, do the following:
- verify the canonical policy files exist
- verify the supporting policy and prompt files exist
- verify `policies/core/runtime/agent/BOOTSTRAP.md` and all attached agent markdown files exist
- verify the operational files exist or create them if missing (under `operations/`):
  - `operations/ORG_REGISTRY.md`
  - `operations/ORG_CHART.md`
  - `operations/AGENT_LIFECYCLE_REGISTER.md`
  - `operations/TASK_STATE_STANDARD.md`
  - `operations/BOARD_REVIEW_REGISTER.md`
  - `operations/CHANNEL_ARCHITECTURE.md`
  - `operations/SECURITY_ALERT_REGISTER.md`
  - `operations/SECURITY_AUDIT_REPORT.md`
  - `operations/SECURITY_REMEDIATION_QUEUE.md`
  - `operations/INCIDENT_REGISTER.md`
- instantiate or define the Chief Orchestrator
- instantiate or define the Org Mapper / HR Controller
- instantiate or define the Chief Security Governor
- instantiate the core security agents
- run startup preflight
- run security audit
- classify findings as INFO / WARNING / CRITICAL
- enter safe mode or refuse activation if required by policy

Only if the environment passes or is warning-only, continue by:
- activating Product, Engineering, Operations, and IT/Security Directors
- preparing standards and cadence files
- activating one Project Lead per real project
- allowing Project Leads to request subordinate agents only as needed
- loading the attached agent markdown pack according to `policies/core/runtime/agent/BOOTSTRAP.md` and `policies/core/runtime/agent/AGENTS.md`

Rules:
- register every agent before activation
- keep memory local by role level and store only active summaries upward; maintain continuous archival writes under `operations/projects/<slug>/memory/archival/` per `policies/core/governance/artifacts-and-archival-memory.md`
- use the warning/critical severity model exactly as defined
- if ambiguity exists, choose the leaner and more restrictive interpretation
- do not treat secondary files as overriding the primary canonical pack

Required output:
- activation status
- canonical policy files verified
- supporting policy files verified
- agent markdown files verified
- agents instantiated or defined
- security status
- warning count
- critical count
- safe mode status
- next recommended step
```

---

## Effective Load Order

Use this order:

1. `policies/core/security-first-setup.md`
2. `policies/core/unified-deployment-and-security.md`
3. `policies/core/deployment-handoff.md`
4. `python policies/core/scripts/start_pipeline.py` — see `policies/core/pipeline-runbook.md`
5. `policies/README.md`
6. `policies/README.md`
7. `policies/core/governance/artifacts-and-archival-memory.md`
8. `policies/core/agentic-company-deployment-pack.md`
9. `policies/core/security-prompts.md`
10. `policies/core/chief-orchestrator-directive.md`
11. `policies/core/runtime/agent/BOOTSTRAP.md`
12. `policies/core/runtime/agent/AGENTS.md`
13. the remaining attached agent markdown files
14. `policies/core/governance/standards/*.md` supporting policies
15. `policies/core/governance/role-prompts/*.md` supporting role templates
16. `operations/` registers and project memory trees
17. `policies/core/governance/generated/` governed additions (indexed in `policies/core/governance/generated/README.md`)

<!-- policy-read-order-nav:bottom -->
> **Next step:** continue to [core/README.md](README.md) after this file is fully read and applied. Do not skip ahead unless a human operator explicitly directs a narrower scope.
<!-- policy-read-order-nav:bottom-end -->
