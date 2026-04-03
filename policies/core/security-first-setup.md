<!-- policy-read-order-nav:top -->
> **Governance read order** — step 1 of 53 in the canonical `policies/` sequence (layer map & tables: [`README.md`](../README.md)).
> **Before this file:** none — this is the **first** document in the sequence. Do not treat later policy files as valid context until this one is understood.
> **This file:** safe to apply only after the prerequisite above (if any) is complete.
<!-- policy-read-order-nav:top-end -->

<!--
  Read order within core/ (flat runbooks): (1) this file — security-first-setup.md
  (2) unified-deployment-and-security.md — full deployment runbook
  (3) deployment-handoff.md — builder/runtime handoff
  Former numeric prefixes: 0000 → this file; 000 → unified runbook; START_HERE → deployment-handoff.md
-->

# Security-first setup

## Purpose

This is the **first file to follow**.

Use it before deploying any policies, prompts, runtime agents, automations, or project workflows.

Its purpose is to help the human operator build a **secure, isolated agent environment** first, so that later deployment happens inside the correct security boundaries rather than trying to retrofit them afterward.

This file is the **human-first setup runbook**.

After completing this file, the next file in the order of operations is:

- `policies/core/unified-deployment-and-security.md`

Then:

- `policies/core/deployment-handoff.md` — drives deployment of the canonical policies, prompts, runbooks, operational records, bootstrap/agent markdown pack, and the `operations/` / `policies/core/governance/generated/` artifact trees.

---

## Required Order of Operations

Follow this order exactly:

1. `policies/core/security-first-setup.md` (this file)
2. `policies/core/unified-deployment-and-security.md`
3. `policies/core/deployment-handoff.md`
4. `policies/core/runtime/agent/BOOTSTRAP.md`
5. `policies/core/runtime/agent/AGENTS.md`
6. the remaining attached agent markdown files referenced by `BOOTSTRAP.md` and `AGENTS.md`

**Within this file (human setup before the policies pipeline):** finish the **environment** (Steps 1–8) → provision **isolated service accounts** and credentials the agent will use (Step 9) → place **deployment entry files** (Step 10) → keep integrations minimal (Step 11) → **validate** (Step 12). **After** `deployment-handoff.md`, when you are ready to verify and index the policy tree, run the pipeline described in [`policies/core/pipeline-runbook.md`](pipeline-runbook.md) (`start_pipeline.py`)—do not treat the pipeline as a substitute for the runbooks.

Do not skip directly to prompts or runtime activation before the environment is isolated and validated.

---

## High-Level Goal

You are setting up **two separate trust zones**:

### Zone A — Workstation (e.g. macOS)

Your real machine. This is the **more sensitive** system for the human operator.

Treat it as containing:

- your normal browser
- your password manager
- operator SSH keys and hardware tokens (when used)
- your important files
- your logged-in sessions

The **long-lived agent/gateway runtime must not run here** at the highest posture. Builder/editors may run here under a **non-admin** account; execution and integrations that define “runtime” belong on **Zone B**.

### Zone B — Runtime (dedicated VPS)

This is the **only** zone where the 24/7 agent, gateway, and automation-adjacent services should live.

Treat it as:

- network-separated from the workstation
- disposable or rebuildable (snapshots, IaC, images)
- tightly scoped
- **non-root for routine operation**
- workspace-only data layout
- browser-isolated (if a browser exists on the server)
- integration-constrained
- safe to wipe or restore from a known-good image

The runtime zone exists so a compromise there does **not** automatically become a compromise of your workstation vault, keys, and personal sessions—**smallest possible blast radius**.

**Optional alternative:** a **dedicated local guest VM** may stand in for a VPS if you enforce the same logical rules (separate non-sudo runtime user, no shared folders/clipboard with the workstation, no vault on the guest). The canonical path described here is **VPS-first**.

---

## macOS account model (strongly recommended)

Use **separate macOS accounts** to separate privilege from daily use:

### Administrator account (bootstrap and maintenance only)

Use **only** for:

- creating the standard user account(s)
- macOS updates that require admin
- **initial VPS provisioning** (first SSH session, cloud-init, firewall baseline) when that step must run locally
- rare break-glass maintenance

**Rules:**

- **Do not** run the AI agent/gateway runtime on this account.
- **Do not** use this account for daily chat, email, or browsing tied to messaging platforms that control the agent.
- **Do not** treat this account as “normal work”—it exists to reduce time-at-high-privilege.

### Standard user account (daily operator)

Create a **fresh Standard user** (no membership in `admin`, no `sudo`) for:

- day-to-day work
- chat clients used to talk to the bot (Telegram, Slack, Discord, etc.) when that is your control path
- editors/builders (e.g. IDE) where the OS allows without elevation

**Rules:**

- **No sudo** for routine work—forces a deliberate switch to admin for anything that mutates the system.
- Prefer **no production SSH keys** on this account; if SSH to the VPS is unavoidable, use a **dedicated key**, passphrase-protected, and **separate** from automation/CI keys.
- **Prefer the chat → gateway → VPS path** for operations instead of routine interactive SSH from the laptop (reduces “message → shell” blast radius).

This split ensures **runtime and routine control-plane traffic** are not tied to an always-admin session on the Mac.

---

## VPS access and network posture (security-critical)

Assume the VPS has a **public IP**. Treat the network as **hostile** unless you explicitly overlay private access.

### Private overlay first

- Put the VPS on a **private tailnet/VPN** (e.g. Tailscale, WireGuard) and **administer over that**, not over raw public SSH.
- If you must expose SSH at all, **restrict by source IP** or VPN-only; avoid `0.0.0.0/0` for SSH.

### SSH hardening (baseline)

- **Key-based auth only**; disable password authentication and **disable root SSH login**.
- **Separate keys**: operator login vs automation/deploy keys; different passphrases; never reuse a personal key across unrelated systems without reason.
- **Avoid SSH agent forwarding** unless you understand the risk (forwarded agent can be abused on the remote side).
- Enable **audit logging** and centralized or tamper-evident logs where feasible; review failed auth and sudo (if any) periodically.

### Firewall

- **Default deny inbound**; allow only required ports (often VPN overlay makes public SSH unnecessary).
- Explicit **egress allowlists** for hardened profiles (model APIs, package mirrors, integrations)—document exceptions; alert on drift.

### Runtime identity on the VPS

- **Provisioning:** root or sudo-capable user **only** for install, kernel updates, and break-glass.
- **Routine:** a **dedicated standard user** for the agent process, workspace, and service units—**no sudo** for that user.

### Chat and messaging as a control plane

Messaging platforms are **semi-trusted**: MFA on operator accounts, **bot token hygiene** (rotation on leak, minimal scopes), **immutable-ID allowlists** (not display names), no open DMs for owner-only actions. Treat inbound messages as **untrusted content** for instruction-following (see canonical security policy).

---

## Secrets and credentials (agent infrastructure)

**Where secrets should live**

- **Canonical store for the agent provider:** API keys, gateway tokens, and tool-related secrets belong under **`AGENT_HOME/.env`** (typically under the agent’s home directory on the machine where the agent runs, e.g. `~/.agent/.env`; with **profiles**, each profile has its own `AGENT_HOME`, so each gets its own `.env`). Setup and CLI flows write here; the file should remain **outside** git and **not** copied into public artifacts.
- **Workstation vs runtime:** On a **VPS runtime**, the same rule applies: secrets for the running gateway/agent live in that host’s **`AGENT_HOME/.env`** (owned by the **runtime user**), not in the application repo. Do **not** put your operator password vault or full production credential stores there—only **narrowly scoped** keys the agent needs.
- **Repository `.env`:** A project-root `.env` may exist for **local development** and is usually gitignored. Treat it as **non-authoritative** and avoid relying on it for production; prefer the agent home **`AGENT_HOME/.env`** (e.g. `~/.agent/.env` on the workstation or the same path on the runtime host) so secrets are not tied to a clone path.

**Posture**

- Long-lived keys in a **plaintext user-only file** (e.g. Unix `chmod` 600) is a common CLI baseline—it is **not** the same as a vault or HSM.
- **Recommendation — before production:** move toward **stronger authentication and storage** than flat files: **hardware security keys** (e.g. FIDO2) and provider flows that **avoid persisting long-lived secrets on disk** where available; **secrets managers** or **runtime injection** (cloud KMS, vault, env from orchestrator) for production; **rotate** keys on any suspected leak.

---

## What You Are Building

Before deploying any runtime policies or prompts, you should end up with:

- one workstation with a **standard daily user** (no sudo) and a **separate admin account** used only for bootstrap/maintenance—not for runtime
- one **dedicated VPS** (or optional guest VM) **only** for the agent/gateway runtime
- on the VPS: one **provisioning** identity (root/sudo) for setup/patching only
- on the VPS: one **runtime user** used only for the running agent and workspace (no sudo)
- one **runtime workspace** with:
  - `workspace/input`
  - `workspace/output`
  - `workspace/logs`
- one **dedicated browser profile** on the runtime host if a browser is used—only for the agent
- **no** mounting workstation directories into the runtime workspace
- **no** password manager or personal vault on the runtime host
- **no** personal/work browser login inside the runtime browser profile
- **no** public exposure of the gateway or browser control
- **no** production SSH targets or production credential stores on the runtime host beyond narrowly scoped secrets
- **API and tool secrets** for the agent held under **`AGENT_HOME/.env`** on the correct host (workstation or VPS), not committed to the repo—see **Secrets and credentials** above
- **Dedicated service identities** for each integration the agent will use (inference providers, Git/forges, messaging bots, optional tool APIs), **and** where applicable an **agent-only** identity for your **IDE / agent-assisted coding environment**—created **before** you run the policies pipeline or expect full automation—see **Step 9**

---

## Step 1 — Harden the Workstation First

The workstation is more sensitive than the runtime. Start there.

Do this:

- keep the OS fully patched
- use a strong login password / FileVault
- enable full-disk encryption
- keep the **password manager on the workstation only** (Standard user)
- keep **long-lived operator secrets** off the VPS except minimal scoped API keys the agent needs
- keep personal browser sessions on the workstation only
- keep sensitive files on the workstation only
- turn on the host firewall
- move toward deny-by-default inbound on the workstation
- do not expose public services from the workstation for this setup

Do not do this:

- do not use the **administrator** macOS account for daily runtime or messaging control
- do not run the **gateway/agent 24/7** on the workstation at highest posture
- do not let the runtime agent attach to your normal browser on the workstation
- do not sync your personal vault or production kubeconfigs onto the VPS “for convenience”

---

## Step 2 — Provision the Runtime VPS

Create or allocate a **dedicated VPS** only for this runtime.

Requirements:

- not shared with unrelated workloads
- treated as disposable/rebuildable
- initial access: prefer **cloud console** or **VPN**, then harden SSH as above
- document provider, region, and **backup/snapshot** strategy before going live

Immediately after the OS is installed:

- install security updates
- create the **runtime** standard user and lock down SSH as above
- take a **snapshot or image** of the clean base
- record the server purpose and **allowed network paths**
- do not log into personal cloud accounts on the VPS
- do not reuse personal workstation identity on the VPS

---

## Step 3 — Separate Provisioning vs Runtime Accounts (on the VPS)

Use two separate Linux accounts (or equivalent).

### Provisioning / maintenance (root or sudo-capable)

Use only for:

- initial OS configuration
- installing approved software and services
- patching
- systemd units that require elevated install
- emergency break-glass recovery

Rules:

- do not run the agent **as root** or as this user for routine operation
- do not browse casually under this identity
- do not use it for day-to-day chat-driven operations

### Runtime user

Use only for:

- running the AI agent / gateway under service supervision
- owning the runtime workspace
- owning the dedicated agent browser profile (if any)

Rules:

- must be a standard user
- must not have sudo capability **for routine operation**
- must not silently elevate

---

## Step 4 — Install Only the Minimum Necessary Software on the VPS

Use the provisioning account for installation.

Install only what you actually need, for example:

- runtime dependencies for the agent
- reverse proxy or VPN client if in architecture
- audit or logging tools you explicitly want

Do not install by default:

- password managers
- personal messaging apps (control plane is via your **workstation** chat clients → gateway on VPS)
- personal cloud-drive sync
- broad developer toolchains you will not use
- Docker socket exposed to the runtime user without hardening review

---

## Step 5 — Set Up the Runtime Workspace

Log in as the **runtime user** and create the workspace.

Create:

- `workspace/input`
- `workspace/output`
- `workspace/logs`

Optionally create:

- `workspace/tmp`
- `workspace/cache`

Rules:

- all runtime file activity should stay inside this workspace
- logs should stay inside `workspace/logs`
- downloads should go into the workspace only
- no broad filesystem roots
- no mounted workstation paths

Make a note of the exact canonical path to this workspace.

---

## Step 6 — Create the Dedicated Agent Browser Profile (if applicable)

If the runtime uses a browser:

Create **one** browser profile only for the runtime agent.

Required properties:

- not logged into personal accounts
- not logged into work accounts
- no sync
- no password manager
- no imported browsing data
- no personal extensions
- downloads restricted to the workspace
- use incognito/ephemeral mode where compatible

Do not attach the agent to a personal browser on the workstation.

---

## Step 7 — Set the Network Posture

Default posture:

- **loopback-only bind** for the runtime/gateway services facing local consumers
- **no** public internet exposure of control surfaces
- **no** public SSH open to the world without VPN/IP restriction
- **no** public browser-control exposure
- remote admin access via **VPN/tailnet** and/or explicit tunnel to loopback
- deny-by-default firewall on the VPS

Do not make anything internet-accessible “just for testing.”

---

## Step 8 — Decide the Builder vs Runtime Split

Before deploying policies, choose who does what.

Recommended split:

### Cursor or equivalent coding agent (on the workstation)

Use as:

- builder
- file-level deployer
- editor

Prefer the **Standard** macOS user without sudo; use admin only when the OS requires it.

### Runtime agent (on the VPS)

Use as:

- activator
- validator
- operator against allowlisted tools
- policy-following executor
- preflight/audit runner

The builder lays the rails. The runtime operates on the rails **on the VPS**.

### Fork upstream and clone on the workstation

When the agent provider publishes source on a **Git forge** (e.g. GitHub-class hosting):

1. **Fork** the upstream repository into the **agent-owned** forge account (the same identity you use for narrowly scoped PATs/SSH keys in Step 9—not your unrelated personal user, when policy requires separation). That fork is where you branch, open pull requests, and attach CI as needed.
2. **Clone** the **fork** (not an anonymous download of upstream only) using your **IDE** or **agent-assisted coding environment**, authenticated as that same agent-scoped forge identity.
3. **Place the working copy** under the **macOS user account where you run the IDE** for daily builder work. In this runbook that is normally the **Standard** user (see **macOS account model** above)—**not** the **administrator** account, which is reserved for bootstrap and system maintenance. A clone that lives only under the administrator home directory is invisible to the Standard user’s sessions unless you duplicate it or use shared storage deliberately.

**Why:** the builder edits policies and code from the workstation; the runtime on the **VPS** may have its **own** clone or deploy artifact—those are separate paths. The workstation clone must be reachable from the account that actually opens the IDE.

---

## Step 9 — Provision isolated service accounts (before the policies pipeline)

After the **runtime environment** exists (workstation split, VPS, workspace, network posture) and **before** you rely on a fully wired agent or run the **policies verification pipeline** (`start_pipeline.py` — see [`policies/core/pipeline-runbook.md`](pipeline-runbook.md)), provision **dedicated identities** for everything the agent provider’s setup, wizard, or runtime will need. Goal: the agent uses **its own** accounts and narrowly scoped tokens—not your personal logins—for routine operation.

### Principle

- **One workload, one identity** where platforms allow it: separate from your day-to-day GitHub user, personal API keys, and personal messaging accounts when policy or risk warrants it.
- **Builder environment:** where you use an **IDE** or other **agent-assisted coding environment** (editor + embedded agent features), use a **dedicated login or profile** for that stack—agent-only—rather than your personal day-to-day identity when policy calls for isolation (see table row below).
- **Least privilege:** read-only or single-repo scopes for Git; minimal chat/API scopes for bots; only the inference providers you actually enable.
- **Secrets only in `AGENT_HOME/.env`** (or your deployment’s equivalent) on the correct host—never committed to the repository. See **Secrets and credentials** above.

### What to create (inventory and check off)

Use the agent provider’s documentation and setup prompts as your checklist. Typical categories:

| Area | What to provision | Isolation note |
|------|-------------------|----------------|
| **Inference / model APIs** | API keys or tokens for each enabled provider (aggregators, direct APIs, optional base URLs) | Separate from personal playground keys if you want a hard split; store only what the runtime needs |
| **Git / forge (GitHub, GitLab, …)** | PAT, fine-grained token, or deploy keys limited to repos the agent may access; optional machine user; **fork** upstream into the agent forge account then **clone** the fork on the workstation (see **Step 8 — Fork upstream and clone**) | Narrow repo/org scope; not your primary SSO identity if you can avoid it |
| **Messaging / gateway** | Bot tokens / app credentials (Telegram bot, Slack app, Discord application, etc.) | Bots are first-class identities; use allowlists and MFA on *your* operator account separately |
| **Search, web, browser automation** | API keys for search, crawling, or remote browser products if those tools are enabled | Dedicated key; rate-limit aware |
| **Cloud & infrastructure** | IAM user, service principal, or API role for any cloud CLIs/APIs the agent will call | Minimal policy; separate from prod admin |
| **Containers / registry** | Read/pull or push credentials only if workflows require them | Scoped registry |
| **MCP, plugins, skills hosts** | Any URLs, tokens, or OAuth clients required by optional integrations | Same rules: dedicated or scoped, not personal vault export |
| **IDE / agent-assisted coding environment** | A **separate** vendor or OS account (or dedicated profile) used only for the editor + embedded agent where the product supports it | Keeps agent chat history, extensions, and sync boundaries off your personal identity; align Git/terminal inside that environment with the same scoped tokens you use for the agent workload |

### IDE and agent-assisted coding environment (agent-only)

If your workflow uses an **IDE** or similar **agent-assisted coding environment** (interactive editor with built-in agent/chat features), provision credentials **used only for that role**:

- Prefer a **dedicated account** or **workspace profile** at the product/OS level when available, so cloud sync, identity, and defaults are not shared with your personal daily profile.
- Sign in to **inference or plugin features** inside that environment with keys or subscriptions scoped to **agent work**, not personal accounts, where you can separate them.
- Match **Git and terminal** identity inside that environment to the **same** narrow tokens and repos you provisioned for the agent (see **Git / forge** above)—avoid mixing personal SSH keys or org-wide access.
- This is **in addition to** the macOS Standard user vs admin split: the IDE/agent coding stack gets its own **logical** identity when you want the smallest blast radius for prompt-injected or tool-mediated actions during development.

### Process

1. **Inventory** every variable or account the setup flow asks for (including “optional” tool APIs you plan to enable soon), **and** whether you will use a dedicated **IDE / agent-assisted coding environment** identity (table row above).
2. **Create** accounts or tokens **before** you need the agent unattended: register bots, create PATs, enable provider billing if required; configure the **agent-only** IDE/coding-environment login or profile when you adopt that split.
3. **Record** values into **`AGENT_HOME/.env`** on the workstation and/or VPS as appropriate; use the **runtime user** on the VPS for runtime-only secrets.
4. **Document** outside the repo (operator runbook) which identity owns which integration, for rotation and incident response.
5. **Do not** run the policies pipeline expecting a green path until **mandatory** secrets for your chosen profile exist if the pipeline or validators depend on them (optional keys can wait).

### Operator accounts vs agent accounts

- **Your** accounts (e.g. messaging login you use to talk to the bot): protect with MFA; they are not the same as **bot tokens** stored on the server.
- **Agent/service** accounts: no human inbox required where bots suffice; prefer tokens that can be rotated without touching your personal SSO.
- **IDE / agent-assisted coding environment (agent-only):** distinct from both—used only for the editor + embedded agent workload when you adopt a separate profile; not a substitute for the **runtime VPS** identity, but part of the same overall isolation story on the workstation.

---

## Step 10 — Prepare the Deployment Entry Files

Before activation, place these entry files where the builder and runtime can access them (paths under this repo):

- `policies/core/security-first-setup.md`
- `policies/core/unified-deployment-and-security.md`
- `policies/core/deployment-handoff.md`
- `policies/core/runtime/agent/BOOTSTRAP.md`
- `policies/core/runtime/agent/AGENTS.md`

The order is intentional (see the “Required Order of Operations” section above).

---

## Step 11 — Keep Integrations Off at First

Before first activation, keep these disabled unless absolutely needed:

- Slack
- Telegram
- Discord
- email
- calendar
- contacts
- notes
- cloud storage
- databases
- external API surfaces
- plugins/hooks/skills
- execution
- browser control beyond what is needed for validation

If you later enable integrations, use:

- immutable IDs
- owner-only approval actions
- read-only scopes where possible
- no config writes from chat by default
- no broad/open DM access by default
- no username/display-name trust where stable IDs exist

---

## Step 12 — Run Manual Human Validation Before Any Agent Activation

Before allowing any runtime agent to activate, manually verify:

### Workstation/runtime separation

- no shared folders from workstation mounted into runtime workspace (if using VM: clipboard/sharing off)
- runtime is on **VPS** (or isolated VM), not on macOS admin account

### Account separation

- macOS **admin** exists and is **not** used for routine runtime
- macOS **Standard** daily user exists without sudo
- VPS **runtime** user exists and is non-sudo for routine work
- provisioning identity on VPS not used for daily agent process

### Browser isolation (if browser on runtime)

- dedicated agent profile exists
- no login / no sync / no password manager
- downloads go to workspace

### Workspace

- workspace exists with input/output/logs
- no workstation mounts inside workspace

### Network posture

- gateway intended to bind loopback (or private interface per policy)
- no public exposure path for control plane
- SSH not world-open without compensating controls
- no full production vault on VPS

### Entry-file readiness

- deployment entry files exist (see Step 10)

### Isolated service accounts

- inference, Git, messaging, and tool API identities created per Step 9 (as applicable)
- **IDE / agent-assisted coding environment:** agent-only login or profile in use where you chose that split (Step 9)
- **Git / workstation:** upstream forked into the agent forge account; working tree cloned where the **IDE runs** (typically the **Standard** macOS user—Step 8), not only under the administrator account
- scopes reviewed; no personal-only credentials required for routine agent operation unless explicitly accepted

### Secrets (agent provider)

- inference and tool API material is under **`AGENT_HOME/.env`** on the host where the agent runs (not committed to the repo)
- production path does not rely on a repo-local `.env` as the sole store

If any of these fail, fix them before moving on.

---

## Step 13 — What Happens Next

Once this file is complete, move immediately to:

- `policies/core/unified-deployment-and-security.md`

After that runbook, use:

- `policies/core/deployment-handoff.md`

That file should:

- direct the builder to deploy against the current policy tree
- direct the runtime to activate from the deployed structure
- explicitly include `BOOTSTRAP.md` in the deployment process
- ensure the bootstrapping process updates or instigates all attached agent markdown files
- ensure the user has a clear handoff into the full operating system

**Policies pipeline (when ready):** after you understand the runbooks and handoff, run the verify/index pipeline as described in [`policies/core/pipeline-runbook.md`](pipeline-runbook.md). That step **refreshes** `policies/INDEX.md` and validates layout—it does not replace environment hardening (Steps 1–8), isolated service accounts (Step 9), or the rest of this runbook.

---

## Minimal First-Step Checklist

1. secure the workstation; keep vault and personal sessions there; use a **Standard** daily user without sudo
2. reserve **macOS admin** for bootstrap/maintenance only—**not** runtime
3. provision a **dedicated VPS** (or isolated guest VM) for runtime only
4. harden SSH, firewall, and VPN/tailnet access; smallest public attack surface
5. separate **provisioning** vs **runtime** Linux accounts on the VPS
6. install only minimum required software on the VPS
7. create the runtime workspace
8. create the dedicated agent browser profile if needed
9. ensure no password manager, no sync, no personal login on runtime
10. set private/loopback posture for services; no public gateway test endpoints
11. **fork** upstream into the agent forge account and **clone** the fork under the **Standard** macOS user (IDE)—see Step 8; provision **isolated service accounts** (inference APIs, Git/forges, messaging bots, tool APIs, cloud/MCP as needed), **and** an **agent-only** identity for your **IDE / agent-assisted coding environment** when using that split; load secrets into **`AGENT_HOME/.env`** — **before** expecting the policies pipeline or unattended runtime
12. place the deployment entry files
13. confirm **agent secrets** live under **`AGENT_HOME/.env`** (not in git); plan **hardware key / vault / injected secrets** before production
14. verify the environment manually (including Step 12)
15. move to `policies/core/unified-deployment-and-security.md`, then `policies/core/deployment-handoff.md`
16. when ready, run the pipeline per [`policies/core/pipeline-runbook.md`](pipeline-runbook.md) (after handoff context—not a substitute for runbooks)

---

## Final Standard

The correct order is:

**secure workstation and accounts → isolate runtime on VPS → split provisioning vs runtime users → create workspace → isolate browser → lock down network posture → provision isolated service accounts (Git, APIs, messaging, tools, IDE/agent coding environment) into `AGENT_HOME/.env` → place entry files → verify environment → deployment handoff → policies pipeline when ready → bootstrap agent pack → activate only after audit**

<!-- policy-read-order-nav:bottom -->
> **Next step:** continue to [core/unified-deployment-and-security.md](unified-deployment-and-security.md) after this file is fully read and applied. Do not skip ahead unless a human operator explicitly directs a narrower scope.
<!-- policy-read-order-nav:bottom-end -->
