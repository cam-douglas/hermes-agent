---
name: autoresearch
description: "CPU autoresearch: ask for program.md + wall-clock minutes, then run the checkout workflow."
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [autoresearch, ml, training, experiment, loop, program-md]
---

# Autoresearch (CPU)

**Slash command:** `/autoresearch` only.

Hermes syncs this skill into **`$HERMES_HOME/skills/software-development/repo-autoresearch-cpu/`** on CLI/gateway start (`sync_skills`). Use the **skills** directory — **not** `skills-repos/` or ad-hoc paths under `/home/hermesuser/skills-repos/autoresearch-cpu` unless the user explicitly chose that layout.

## Required interactive setup (do not skip)

When `/autoresearch` fires, **stop and ask** before any training or repo commands:

1. **program.md** — Ask the user to **paste the full body** for `program.md` (experiment brief), or to provide a **file path** you can read.
2. **Outer runtime** — Ask: *How many minutes of wall-clock time should the Hermes autoresearch tool loop run?* (one integer). **Do not** invent this value.

Then merge answers into a single `program.md` with `# autoresearch` in the first ~120 lines and an explicit line such as `Outer runtime: <N> minutes`, set `HERMES_AUTORESEARCH_OUTER_MINUTES=<N>` when useful, and continue.

## Training code location (canonical)

- **Skill root:** `$HERMES_HOME/skills/software-development/repo-autoresearch-cpu/`
- **Working tree / clone target:** `…/repo-autoresearch-cpu/checkout/`
- **program.md (default for engine):** `…/checkout/program.md`  
  (Or set `HERMES_AUTORESEARCH_PROGRAM` to another absolute path.)

If `checkout/` is empty or has no git remote, clone the upstream repo **into** `checkout/`:

```bash
git clone https://github.com/cam-douglas/autoresearch-cpu.git "$HERMES_HOME/skills/software-development/repo-autoresearch-cpu/checkout"
```

(If `checkout` already exists non-empty, clone into a temp dir and move, or `git pull` — avoid nesting another `autoresearch-cpu` folder inside `checkout`.)

## Dependencies (prefer portable installs)

1. **Python 3** — Required. A project **venv** under `checkout/.venv` or `checkout/venv` is recommended.
2. **`uv`** — Optional speed-up. If `command -v uv` fails, **do not** assume `uv run` works; use `python3 -m pip install -r requirements.txt` (or the repo’s documented install) and run `python3 prepare.py` / `python3 train.py` instead.
3. After deps are present, typical flow (adjust to repo README):

```bash
cd "$HERMES_HOME/skills/software-development/repo-autoresearch-cpu/checkout"
# If using uv and it is installed:
# uv sync && uv run prepare.py --num-shards 4 && uv run train.py
# Otherwise (venv activated):
# python3 -m pip install -e .   # or pip install -r requirements.txt
# python3 prepare.py --num-shards 4
# python3 train.py
```

## Runtime integration

- Hermes reads `program.md` / env and raises the tool-loop iteration cap until the **outer wall-clock** budget is reached.
- See `docs/hermes-autoresearch-one-step.md` for the full playbook.

## Observability (second terminal)

When a new autoresearch wall-clock window arms, Hermes prints color-highlighted commands (`hermes logs -f --session …`, `hermes chat --continue …`), **exact copy-paste** lines to run `prepare.py` / `train.py` in a second terminal (using `python3` or the checkout venv; `uv run` only if `uv` is on PATH), and writes `$HERMES_HOME/autoresearch_wallclock_state.json` (same strings as `prepare_recommended_cmd` / `train_recommended_cmd`). If stdout is suppressed, read the same commands from that JSON or the session log.
