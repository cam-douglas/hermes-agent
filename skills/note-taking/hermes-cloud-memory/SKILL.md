---
name: hermes-cloud-memory
description: "Hermes external memory providers — CLI, config, and every agent tool name with parameters (Honcho, Mem0, LanceDB, Hindsight, OpenViking, RetainDB, Supermemory, ByteRover, Holographic) plus related cloud env keys."
version: 1.0.0
author: community
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Memory, Mem0, Honcho, LanceDB, Hindsight, RetainDB, Zep, Letta, LangSmith, Config]
---

# Hermes cloud and external memory

Hermes keeps **built-in** session memory (`MEMORY.md` / `USER.md` under `$HERMES_HOME/memories/`) **always**. **At most one** external `memory.provider` is active at a time (`config.yaml`). Only that provider’s **tools** are registered for the agent.

## CLI commands (shell)

```bash
# Interactive wizard: pick provider, write config + .env
hermes memory setup

# Show active provider and config hints
hermes memory status

# Turn off external provider (built-in memory only)
hermes memory off

# Erase built-in markdown memory files (not cloud backends)
hermes memory reset              # all
hermes memory reset --target memory
hermes memory reset --target user

# Set provider without wizard
hermes config set memory.provider honcho
hermes config set memory.provider mem0
hermes config set memory.provider lancedb
hermes config set memory.provider hindsight
hermes config set memory.provider openviking
hermes config set memory.provider retaindb
hermes config set memory.provider supermemory
hermes config set memory.provider byterover
hermes config set memory.provider holographic
hermes config set memory.provider ""   # same as memory off

# Health / deps
hermes doctor
```

### Honcho-specific CLI (when using Honcho)

Honcho is also exposed as a top-level command group:

```bash
hermes honcho setup
hermes honcho status
hermes honcho sessions
hermes honcho map <name>
hermes honcho peer
hermes honcho peer --user NAME
hermes honcho peer --ai NAME
hermes honcho peer --reasoning LEVEL
hermes honcho mode
hermes honcho mode hybrid|honcho|local
hermes honcho tokens
hermes honcho tokens --context N
hermes honcho tokens --dialectic N
hermes honcho identity
hermes honcho identity <file>
hermes honcho migrate
```

## Agent tools by provider (call these exact function names)

Below, **required** parameters must be supplied. Optional ones can be omitted unless you need them.

### Honcho (`memory.provider: honcho`)

| Tool | Required args | Optional args |
|------|----------------|----------------|
| `honcho_profile` | — | `peer` (`user` / `ai` / id), `card` (array of strings — if set, updates card) |
| `honcho_search` | `query` | `peer`, `max_tokens` |
| `honcho_reasoning` | `query` | `peer`, `reasoning_level` ∈ `minimal`, `low`, `medium`, `high`, `max` |
| `honcho_context` | — | `query`, `peer` |
| `honcho_conclude` | exactly one of `conclusion` **or** `delete_id` | `peer` |

### Mem0 (`memory.provider: mem0`)

| Tool | Required args | Optional args |
|------|----------------|----------------|
| `mem0_profile` | — | — |
| `mem0_search` | `query` | `rerank` (bool), `top_k` |
| `mem0_conclude` | `conclusion` | — |

### LanceDB (`memory.provider: lancedb`)

| Tool | Required args | Optional args |
|------|----------------|----------------|
| `lancedb_profile` | — | — |
| `lancedb_search` | `query` | `top_k` |
| `lancedb_remember` | `text` | — |

Local DB path / embeddings: see `plugins/memory/lancedb/__init__.py` (env `LANCEDB_URI`, `OPENAI_API_KEY` or `LANCEDB_EMBEDDING_*`).

### Hindsight (`memory.provider: hindsight`)

| Tool | Required args | Optional args |
|------|----------------|----------------|
| `hindsight_retain` | `content` | `context`, `tags` (string array) |
| `hindsight_recall` | `query` | — |
| `hindsight_reflect` | `query` | — |

### OpenViking (`memory.provider: openviking`)

| Tool | Required args | Optional args |
|------|----------------|----------------|
| `viking_search` | `query` | `mode` ∈ `auto`, `fast`, `deep`; `scope` (viking:// prefix); `limit` |
| `viking_read` | `uri` | `level` ∈ `abstract`, `overview`, `full` |
| `viking_browse` | `action` ∈ `tree`, `list`, `stat` | `path` (viking URI path) |
| `viking_remember` | `content` | `category` ∈ `preference`, `entity`, `event`, `case`, `pattern` |
| `viking_add_resource` | `url` | `reason`, `to`, `parent`, `instruction`, `wait`, `timeout` |

Env: `OPENVIKING_ENDPOINT`, `OPENVIKING_API_KEY`, `OPENVIKING_ACCOUNT`, `OPENVIKING_USER`, `OPENVIKING_AGENT`.

### RetainDB (`memory.provider: retaindb`)

| Tool | Required args | Optional args |
|------|----------------|----------------|
| `retaindb_profile` | — | — |
| `retaindb_search` | `query` | `top_k` |
| `retaindb_context` | `query` | — |
| `retaindb_remember` | `content` | `memory_type` ∈ `factual`, `preference`, `goal`, `instruction`, `event`, `opinion`; `importance` |
| `retaindb_forget` | `memory_id` | — |
| `retaindb_upload_file` | `local_path` | `remote_path`, `scope` ∈ `USER`, `PROJECT`, `ORG`, `ingest` |
| `retaindb_list_files` | — | `prefix`, `limit` |
| `retaindb_read_file` | `file_id` | — |
| `retaindb_ingest_file` | `file_id` | — |
| `retaindb_delete_file` | `file_id` | — |

Env: `RETAINDB_API_KEY`, `RETAINDB_BASE_URL`, `RETAINDB_PROJECT`.

### Supermemory (`memory.provider: supermemory`)

| Tool | Required args | Optional args |
|------|----------------|----------------|
| `supermemory_store` | `content` | `metadata` (object) |
| `supermemory_search` | `query` | `limit` (1–20) |
| `supermemory_forget` | — | `id` and/or `query` (see tool behavior — provide at least one to delete) |
| `supermemory_profile` | — | `query` |

Env / config: `SUPERMEMORY_API_KEY`, `$HERMES_HOME/supermemory.json` for tuning.

### ByteRover (`memory.provider: byterover`)

Requires `brv` CLI installed.

| Tool | Required args | Optional args |
|------|----------------|----------------|
| `brv_query` | `query` | — |
| `brv_curate` | `content` | — |
| `brv_status` | — | — |

### Holographic / hermes-memory-store (`memory.provider: holographic`)

| Tool | Required args | Optional args |
|------|----------------|----------------|
| `fact_store` | `action` ∈ `add`, `search`, `probe`, `related`, `reason`, `contradict`, `update`, `remove`, `list` | `content`, `query`, `entity`, `entities`, `fact_id`, `category`, `tags`, `trust_delta`, `min_trust`, `limit` (depends on `action`) |
| `fact_feedback` | `action` ∈ `helpful`, `unhelpful`, `fact_id` | — |

## Related cloud keys (not Hermes `memory.provider` tools)

These are common when you run **other** stacks beside Hermes. Hermes does **not** register Zep / Letta / LangSmith / LangMem as memory tools unless you add a custom plugin.

| Service | Typical env | Notes |
|---------|-------------|--------|
| Zep | `ZEP_API_KEY` | Zep Cloud REST / Python SDK — use outside Hermes or via a future plugin. |
| Letta | `LETTA_API_KEY` | Letta REST client — same as above. |
| LangSmith | `LANGSMITH_API_KEY`, often `LANGCHAIN_TRACING_V2=true` | Tracing for LangChain/LangGraph apps. |
| LangMem | (varies) | No bundled Hermes `MemoryProvider` for LangMem in-repo; use LangGraph/LangChain docs. |

For **Mem0**, **Hindsight**, **RetainDB**, **Supermemory**, etc., follow each plugin’s `plugin.yaml` `pip_dependencies` and provider `get_config_schema()` / `hermes memory setup`.

## Doctor and optional skips

- `hermes doctor` includes a **Memory Provider** section for the active provider.
- Tool availability warnings can be reduced with `HERMES_DOCTOR_SKIP_TOOLSETS` (comma-separated toolset ids).
- Spotify / Discord tool warnings are silenced by default unless `HERMES_DOCTOR_STRICT_INTEGRATIONS=1` (see `hermes_cli/doctor.py`).

## Quick decision guide

1. **Pick one** `memory.provider` aligned with your backend (cloud API vs local LanceDB vs Honcho dialectic, etc.).
2. Run `hermes memory setup` or `hermes config set memory.provider …` and fill `.env`.
3. Use **`hermes doctor`** until the provider shows connected.
4. In chat, call **only** the tools listed above for that provider; other providers’ tools will not exist in the session.
