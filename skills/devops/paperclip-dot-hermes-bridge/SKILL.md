---
name: paperclip-dot-hermes-bridge
description: >-
  Connect Hermes to Paperclip (paperclip.inc): host the real server on Fly/Railway/VPS +
  Postgres, set PAPERCLIP_PUBLIC_BASE_URL in Hermes and on the Vercel dot-hermes project so
  /paperclip opens the control plane. Use when the user wants /paperclip or Vercel dot-hermes
  with Paperclip.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [paperclip, vercel, dot-hermes, postgres, deploy]
---

# Paperclip + Hermes + dot-hermes (Vercel)

## Reality check

- **`@paperclipai/server`** is a **long-running Node** app (PostgreSQL, WebSockets, migrations). It is **not** a Vercel serverless app. See [Paperclip deploy docs](https://paperclip.inc/docs/deploy/overview).
- **dot-hermes** on Vercel hosts a **small hub**: `/paperclip` redirects browsers to your real Paperclip HTTPS URL via `PAPERCLIP_PUBLIC_BASE_URL` set in **Vercel project env**. Hermes agents use the **same variable** in `HERMES_HOME/.env` for prompts and `hermes doctor`.
- This matches “use Paperclip like the Cursor workflow”: one canonical URL for humans; Hermes knows it from env.

## Database + Railway (run the server properly)

- **Fast path:** Use Railway’s **Paperclip** template — Postgres and `DATABASE_URL` are wired to the app. See **`docs/paperclip-railway-vercel.md`** (CLI tokens, `railway.json`, `PAPERCLIP_PUBLIC_URL` vs `PAPERCLIP_PUBLIC_BASE_URL`).
- **Vercel’s Railway integration** provisions Postgres and syncs **`DATABASE_URL`** into your **Vercel** project. That does **not** run Paperclip; copy/use that URL on the **host where Paperclip runs** (or deploy Paperclip on Railway next to the same DB). Details in the same doc.

## What you do once

### 1. Run Paperclip for real

Deploy with **`authenticated` + `public`**, hosted Postgres (`DATABASE_URL`), and a stable HTTPS origin. Examples: Fly Machines, Railway, Render, EC2 + Docker. Complete Paperclip’s production checklist (login, `PUBLIC_URL`, etc.) per their docs.

### 2. Hermes (`HERMES_HOME/.env`)

```bash
PAPERCLIP_PUBLIC_BASE_URL=https://your-paperclip.example
# optional stable Vercel production URL (for system prompt hints):
DOT_HERMES_PUBLIC_URL=https://dot-hermes.vercel.app
```

Restart gateway / TUI so env loads.

### 3. Vercel project `dot-hermes`

In the Vercel dashboard for **dot-hermes**, set:

- **`PAPERCLIP_PUBLIC_BASE_URL`** — same value as Hermes (required for `/paperclip` redirect page).

Redeploy from repo **`hermes-agent/.hermes`** (or connected Git root pointing at that directory).

### 4. Verify

- Open `https://<your-dot-hermes>/paperclip` — should redirect to Paperclip.
- `hermes paperclip` — prints configured URLs.
- `hermes paperclip deploy` — headless checklist + Railway template link (no Cursor).
- `hermes doctor` — HTTP check when `PAPERCLIP_PUBLIC_BASE_URL` is set.

## Local monorepo (`repo-paperclip` skill)

If you clone Paperclip under `HERMES_HOME/skills/software-development/repo-paperclip/checkout` and **`pnpm install` fails with EPERM/EACCES** on `packages/*/dist`, generated files are often **owned by root** (Docker bind mounts or `sudo pnpm`).

1. Run **`hermes paperclip fix-checkout`** (or `hermes paperclip fix-checkout --path <checkout-root>`).
2. Retry **`pnpm install`** then **`pnpm dev`**.

Hermes cannot deploy Railway/Fly for you without your cloud tokens; production remains one-click via the Railway template, then set `PAPERCLIP_PUBLIC_BASE_URL` as above.

## Hermes adapter “not found in PATH” (Paperclip UI)

Paperclip’s **Hermes Agent** adapter runs `hermes --version`. If the server uses a **minimal PATH** (systemd, Docker, hosted runners) and Hermes is only installed in a **venv**, the check fails even when `python3 -m hermes_cli.main --version` works.

**Fix:** Use the patched adapter vendored in this repo: `hermes-agent/contrib/hermes-paperclip-adapter` (see its README). From your Paperclip checkout:

```bash
pnpm add "file:/absolute/path/to/hermes-agent/contrib/hermes-paperclip-adapter"
```

Rebuild/restart Paperclip. The adapter tries `~/.local/bin/hermes`, Homebrew paths, and `HERMES_AGENT_REPO/venv/bin/hermes` when `hermes` is missing from the server `PATH`. You can also set **`HERMES_CLI`** to the absolute shim path (`which hermes`) in the environment of the Paperclip **server** process.

Alternatively, put the venv `bin` on the **server** process `PATH`, or set the agent’s **custom Hermes command** to the absolute path of the `hermes` binary.

## Agent behavior

- Hermes **does not start** the Paperclip Node process; it **links** to your deployment.
- Prefer **`hermes paperclip`** and **`skills/devops/dot-hermes-git-sync`** when `.hermes` layout or Vercel files change so the submodule stays consistent.
