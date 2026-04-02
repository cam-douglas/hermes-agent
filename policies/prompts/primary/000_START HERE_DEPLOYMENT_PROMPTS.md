# START HERE_DEPLOYMENT_PROMPTS.md

```text
Review the existing workspace and deploy against the current policy structure rather than rebuilding the architecture from scratch.

The authoritative files already exist. Preserve the current `policies/` hierarchy unless a change is required for operational compatibility.

Authoritative entrypoints:
- `policies/primary/01_CANONICAL_AGENTIC_COMPANY_AND_SECURITY_DEPLOYMENT_PACK.md`
- `policies/runbooks/UNIFIED_DEPLOYMENT_AND_SECURITY_RUNBOOK.md`

Primary prompt files:
- `policies/prompts/primary/00_AI_AGENT_SECURITY_PROMPTS.md`
- `policies/prompts/primary/01_CHIEF ORCHESTRATOR IMPLEMENTATION DIRECTIVE.md`

Supporting policy and template sources:
- `policies/00_CANONICAL_AI_AGENT_SECURITY_POLICY.md`
- `policies/03_ORG_MAPPER_HR_POLICY.md`
- `policies/04_FUNCTIONAL_DIRECTOR_POLICY_TEMPLATE.md`
- `policies/05_PROJECT_LEAD_POLICY_TEMPLATE.md`
- `policies/06_SUPERVISOR_POLICY_TEMPLATE.md`
- `policies/07_WORKER_SPECIALIST_POLICY_TEMPLATE.md`
- `policies/08_BOARD_OF_DIRECTORS_REVIEW_POLICY.md`
- `policies/09_TASK_STATE_AND_EVIDENCE_POLICY.md`
- `policies/10_CHANNEL_ARCHITECTURE_POLICY.md`
- `policies/11_CLIENT_DEPLOYMENT_POLICY.md`
- `policies/12_AGENT_LIFECYCLE_AND_ORG_HYGIENE_POLICY.md`
- `policies/13_AGENTIC_COMPANY_TEMPLATE.md`
- `policies/prompts/02_ORG MAPPER & HR CONTROLLER.md`
- `policies/prompts/03_FUNCTIONAL DIRECTOR TEMPLATE.md`
- `policies/prompts/04_PROJECT LEAD TEMPLATE.md`
- `policies/prompts/05_SUPERVISOR TEMPLATE.md`
- `policies/prompts/06_WORKER & SPECIALIST TEMPLATE.md`
- `policies/prompts/07_BOARD OF DIRECTORS REVIEW.md`
- `policies/prompts/08_CLIENT INTAKE & DEPLOYMENT TEMPLATE.md`
- `policies/prompts/09_MARKDOWN PLAYBOOK GENERATOR.md`
- `policies/prompts/10_FUTURE CHANNEL ARCHITECTURE PLANNER.md`
- `policies/prompts/11_AGENT LIFECYCLE AND ORG HYGIENE CONTROLLER.md`
- `policies/prompts/12_TASK STATE AND EVIDENCE ENFORCER.md`
- `policies/prompts/13_MINIMAL DEFAULT DEPLOYMENT ORDER.md`

Your role is builder and file-level deployer, not policy author. Do not redesign the architecture unless a contradiction prevents implementation.

Tasks:
1. Verify the `policies/` tree exists and is readable.
2. Treat `policies/primary/01_CANONICAL_AGENTIC_COMPANY_AND_SECURITY_DEPLOYMENT_PACK.md` as the canonical entrypoint.
3. Treat `policies/runbooks/UNIFIED_DEPLOYMENT_AND_SECURITY_RUNBOOK.md` as the canonical operational runbook.
4. Treat the two files in `policies/prompts/primary/` as the primary activation prompt sources.
5. Preserve the numbered structure and current folder layout unless a runtime compatibility issue requires change.
6. Create or initialize the operational files required by the runbook if they do not already exist:
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
7. Prefer creating those operational files in a clean runtime/operations area rather than duplicating the policy files.
8. Create any supporting folders, registries, templates, and operational files required by the runbook, but do not clone or duplicate the canonical policy documents unnecessarily.
9. Do not activate agents yourself unless explicitly required by runtime design.
10. Do not weaken any security or governance rule for convenience.
11. If there is ambiguity, choose the leanest, most auditable implementation consistent with the current canonical pack.

Output a concise deployment summary showing:
- files verified
- artifacts cleaned or ignored
- files created
- directories created
- unresolved ambiguities
- anything intentionally left for runtime activation
```

---

## Runtime Activation Prompt

```text
The deployment files, policies, prompts, registries, and runbooks already exist in this workspace under the `policies/` hierarchy.

Your role is not to redesign the system. Your role is to activate, validate, and operate the deployed architecture in strict compliance with the existing canonical pack and runbook.

Use this exact load order:

1. Canonical entrypoint:
   - `policies/primary/01_CANONICAL_AGENTIC_COMPANY_AND_SECURITY_DEPLOYMENT_PACK.md`
2. Canonical runbook:
   - `policies/runbooks/UNIFIED_DEPLOYMENT_AND_SECURITY_RUNBOOK.md`
3. Primary prompt packs:
   - `policies/prompts/primary/00_AI_AGENT_SECURITY_PROMPTS.md`
   - `policies/prompts/primary/01_CHIEF ORCHESTRATOR IMPLEMENTATION DIRECTIVE.md`
4. Secondary supporting policy files in `policies/`
5. Secondary supporting role templates in `policies/prompts/`

Activation rules:
1. Treat `policies/primary/01_CANONICAL_AGENTIC_COMPANY_AND_SECURITY_DEPLOYMENT_PACK.md` as authoritative.
2. Treat `policies/runbooks/UNIFIED_DEPLOYMENT_AND_SECURITY_RUNBOOK.md` as the operational procedure.
3. Do not create ad hoc structure outside the canonical framework unless runtime operation strictly requires it.
4. Do not duplicate or rename policy files unless necessary for compatibility.
5. Do not activate broad execution or project work until the security foundation is active.

Before broader activation, do the following:
- verify the canonical files exist at the paths above
- verify the supporting policy and prompt files exist
- verify the operational files exist or create them if missing:
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

Rules:
- register every agent before activation
- keep memory local by role level and store only active summaries upward
- use the warning/critical severity model exactly as defined
- if ambiguity exists, choose the leaner and more restrictive interpretation
- do not treat secondary files as overriding the primary canonical pack

Required output:
- activation status
- canonical files verified
- supporting files verified
- artifacts ignored or cleaned
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

1. `policies/primary/01_CANONICAL_AGENTIC_COMPANY_AND_SECURITY_DEPLOYMENT_PACK.md`
2. `policies/runbooks/UNIFIED_DEPLOYMENT_AND_SECURITY_RUNBOOK.md`
3. `policies/prompts/primary/00_AI_AGENT_SECURITY_PROMPTS.md`
4. `policies/prompts/primary/01_CHIEF ORCHESTRATOR IMPLEMENTATION DIRECTIVE.md`
5. `policies/*.md` supporting policies
6. `policies/prompts/*.md` supporting role templates
7. generated runtime/registry/audit files
