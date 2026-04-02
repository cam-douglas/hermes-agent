# TASK_STATE_AND_EVIDENCE_POLICY.md

## Purpose

This policy governs task state clarity and evidence-based completion across the entire architecture.

---

## Approved Task States

- Active
- Blocked
- Inactive
- Complete
- Archived

---

## Hard Rules

1. Every task must always have one explicit state.
2. No task may be marked Complete without evidence.
3. No Active task may lack a next action.
4. Every Blocked task must include the blocking dependency or missing decision.
5. Every Inactive task must include the reason for inactivity.
6. Every Archived task must include the reason for archival and a retrieval reference.
7. State changes must be tracked at the appropriate level and summarized upward concisely.
8. Higher levels should retain only the latest relevant task state, not full historical logs.

---

## Valid Evidence Examples

- code committed
- file created
- test passed
- workflow executed
- deployment verified
- document updated
- approval recorded
- issue resolved
- artifact delivered

---

## Standard State Update Format

- task
- prior state
- new state
- reason
- evidence
- next action
- archive recommendation, if applicable