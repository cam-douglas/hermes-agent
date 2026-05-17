# hermes-paperclip-adapter (vendored patch)

This tree is a **fork of [NousResearch/hermes-paperclip-adapter](https://github.com/NousResearch/hermes-paperclip-adapter)** with one behavioral fix:

- **CLI resolution:** If `hermes` is not on `PATH`, the adapter tries  
  `python3 -m hermes_cli.main` / `python -m hermes_cli.main` (same idea as Hermes gateway `_resolve_hermes_bin`).  
  That fixes Paperclip “Adapter environment check” failures when Hermes is installed in a venv but the Paperclip server process does not inherit the venv’s `bin` directory on `PATH`.

Version here: **0.3.2** (not yet published to npm).

## Use in a Paperclip checkout

From the Paperclip repo root (or `server/` if dependencies live there — match your workspace):

```bash
pnpm add "file:/absolute/path/to/hermes-agent/contrib/hermes-paperclip-adapter"
# or npm install "file:..."
```

Then rebuild/restart the Paperclip server.

## Upstream

Please contribute this back to NousResearch when convenient; until then, use this `file:` dependency or copy the `src/server/resolve-hermes.ts` + edits to `test.ts` / `execute.ts` into your own fork.
