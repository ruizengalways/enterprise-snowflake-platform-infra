# Bootstrap Handoff Control Plane

## Status

Source/static implementation exists on the current feature branch. Live DEV deployment and source integration are not yet proven.

## Purpose

`PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP` governs the one-time transition from an initial consistent source snapshot to normal checkpoint-driven incremental or CDC execution.

This document is for people. Machine state and generated authorization surfaces live under `snowflake/control/operations/`; source handoff semantics live in project RAW contracts.

## Ownership

```text
project RAW contract
  owns desired bootstrap semantics

source/domain implementation
  owns vendor-specific boundary capture and consistent snapshot mechanics

PLATFORM_CONTROL
  owns mutable bootstrap lifecycle state and checkpoint commit

framework
  owns bounded metadata validation and domain-scoped call generation
```

Do not put source-specific extraction SQL, LSN logic, API cursor code, or business payloads in `PLATFORM_CONTROL`.

## State machine

```text
BOUNDARY_CAPTURED
    -> SNAPSHOT_LANDED
    -> SNAPSHOT_VALIDATED
    -> HANDOFF_COMMITTED
```

Each transition is performed through an owner-rights procedure whose project and environment are fixed in generated SQL.

A repeated call with already-recorded state is treated as an idempotent retry where the persisted lifecycle proves the operation already completed. Conflicting boundary metadata, snapshot identity, or reconciliation evidence fails closed. A caller cannot skip a state or mutate a committed handoff boundary.

`SNAPSHOT_VALIDATED` requires two distinct inputs: an explicit `reconciliation_passed = TRUE` outcome and non-null reconciliation details. Structured details are audit evidence, not the authorization signal. Passing JSON that merely says `status=PASS` is not sufficient, and `FALSE`/`NULL` is rejected by the platform procedure.

## Initial-bootstrap checkpoint guards

This state machine is only for a dataset's initial handoff into steady-state capture.

`PIPELINE_BOOTSTRAP_START` rejects a dataset/checkpoint kind that already has a `PIPELINE_CHECKPOINT`. Re-seeding or resetting an already-running dataset must use a separate future recovery/reseed workflow rather than silently reusing initial bootstrap.

At final commit the procedure checks again. If an existing checkpoint differs from the captured handoff position, the handoff fails instead of overwriting it. This prevents a delayed bootstrap from rewinding already-progressed steady-state capture.

## Atomic handoff invariant

The final procedure is the authorization and transaction boundary:

```text
SNAPSHOT_VALIDATED
  -> validate any existing checkpoint is absent or equals handoff position
  -> transaction-scoped block
       BEGIN TRANSACTION
       MERGE steady-state PIPELINE_CHECKPOINT = captured handoff position
       UPDATE bootstrap STATUS = HANDOFF_COMMITTED
       COMMIT
       on transaction-block error: ROLLBACK + re-raise
```

Precondition failures occur outside the transaction-scoped exception handler. The explicit rollback handler covers only statements after `BEGIN TRANSACTION`, so state-validation errors are not obscured by an unrelated rollback attempt.

This prevents the dangerous partial state where the incremental checkpoint has advanced but the initial snapshot has not actually passed reconciliation.

## Domain isolation

The shared base table is never directly granted to project deployment roles.

For every configured domain/environment the generator creates:

```text
<DOMAIN>_PIPELINE_BOOTSTRAP                         secure read view
<DOMAIN>_PIPELINE_BOOTSTRAP_START                  owner-rights procedure
<DOMAIN>_PIPELINE_BOOTSTRAP_MARK_SNAPSHOT_LANDED   owner-rights procedure
<DOMAIN>_PIPELINE_BOOTSTRAP_MARK_VALIDATED         owner-rights procedure
<DOMAIN>_PIPELINE_BOOTSTRAP_COMMIT_HANDOFF          owner-rights procedure
```

The generated view filters both `PROJECT_CODE` and `ENVIRONMENT`. Procedures embed those values server-side and expose neither `P_PROJECT_CODE` nor `P_ENVIRONMENT`.

## Single-writer assumption

The current baseline keeps the same operational assumption as checkpoint advancement: one logical bootstrap writer per domain/dataset bootstrap lifecycle. Snowflake standard-table primary-key constraints are not being treated as a substitute for that runtime assumption. Static CI proves fail-closed state transitions and atomic SQL shape; live DEV must still test concurrent retry behavior before production approval.

## Live DEV acceptance criteria

A real source bootstrap is not considered proven until DEV demonstrates all of the following:

1. capture a real source handoff boundary;
2. land a snapshot consistent with that boundary using the source's supported mechanism;
3. produce explicit reconciliation evidence and prove `FALSE` cannot advance validation;
4. reject handoff commit before validation;
5. reject initial bootstrap when a steady-state checkpoint already exists;
6. reject a final handoff that conflicts with a different checkpoint value;
7. atomically commit checkpoint plus `HANDOFF_COMMITTED` after validation;
8. resume steady-state capture with the declared exclusive/inclusive boundary semantics;
9. retry every lifecycle step without uncontrolled double-apply;
10. prove HEALTH cannot read/invoke TRANSPORT bootstrap surfaces and vice versa;
11. prove project roles have no direct DML on `PIPELINE_BOOTSTRAP` or `PIPELINE_CHECKPOINT`.

## Deliberate non-goals

This control plane does not standardize vendor-specific snapshot or CDC setup. SQL Server LSNs, database transaction snapshots, API cursors, Kafka offsets, and similar mechanisms are adapted by the source implementation into the generic handoff position only when the source can actually guarantee the declared semantics.
