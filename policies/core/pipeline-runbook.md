<!-- policy-read-order-nav:top -->
> **Governance read order** — step 8 of 53 in the canonical `policies/` sequence (layer map & tables: [`README.md`](../README.md)).
> **Before this file:** read [README.md](../README.md) and everything earlier in that sequence. **Do not** interpret this document as authoritative until those prerequisites are satisfied.
> **This file:** safe to apply only after the prerequisite above (if any) is complete.
<!-- policy-read-order-nav:top-end -->

# Pipeline runbook (agents)

<!--
  Prerequisites (do not skip): read [`core/README.md`](README.md) — both runbooks,
  then [`deployment-handoff.md`](deployment-handoff.md). This script only validates files and
  refreshes indexes; it does not replace that context.
-->

**Run from the repository root** after the two runbooks, [`deployment-handoff.md`](deployment-handoff.md), and (when you are ready) the constitutional packs in this folder — this file is **only** for running the verify/index **pipeline**:

```bash
python policies/core/scripts/start_pipeline.py --dry-run   # validate only (writes nothing)
python policies/core/scripts/start_pipeline.py             # verify, refresh INDEX.md, update change manifest
```

Or:

```bash
./policies/start_pipeline.sh --dry-run
./policies/start_pipeline.sh
```

Optional: create missing `operations/*.md` stubs (non-destructive):

```bash
python policies/core/scripts/start_pipeline.py --init-operations
```

**What it does**

1. **Strict verification** — required layout; every `policies/core/governance/standards/*.md` must contain an activation-prompt heading (so policies cannot silently pass as empty stubs).
2. **Regenerates** `policies/INDEX.md`.
3. **Writes** `policies/.pipeline_state/manifest.json` (gitignored) to detect future edits.

**Tests:** `pytest tests/policies/test_policy_pipeline.py`

**Full read sequence:** [`../README.md`](../README.md) (layer map & step tables) · scripts: [`scripts/README.md`](scripts/README.md).

<!-- policy-read-order-nav:bottom -->
> **Next step:** continue to [core/security-prompts.md](security-prompts.md) after this file is fully read and applied. Do not skip ahead unless a human operator explicitly directs a narrower scope.
<!-- policy-read-order-nav:bottom-end -->
