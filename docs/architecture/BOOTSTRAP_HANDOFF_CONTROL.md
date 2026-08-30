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

A repeated call with the same already-recorded state is treated as an idempotent retry where safe. A caller cannot skip a state or mutate a committed handoff boundary.

## Atomic handoff invariant

The final procedure is the authorization and transaction boundary:

```text
SNAPSHOT_VALIDATED
  -> BEGIN TRANSACTION
       MERGE steady-state PIPELINE_CHECKPOINT = captured handoff position
       UPDATE bootstrap STATUS = HANDOFF_COMMITTED
     COMMIT
```

If either write fails, the procedure rolls the transaction back and re-raises the error.

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

The current baseline keeps the same operational assumption as checkpoint advancement: one logical bootstrap writer per domain/dataset bootstrap lifecycle. Static CI proves fail-closed state transitions and atomic SQL shape; live DEV must still test concurrent retry behavior before production approval.

## Live DEV acceptance criteria

A real source bootstrap is not considered proven until DEV demonstrates all of the following:

1. capture a real source handoff boundary;
2. land a snapshot consistent with that boundary using the source's supported mechanism;
3. reconcile the landed snapshot;
4. reject handoff commit before validation;
5. atomically commit checkpoint plus `HANDOFF_COMMITTED` after validation;
6. resume steady-state capture with the declared exclusive/inclusive boundary semantics;
7. retry every lifecycle step without uncontrolled double-apply;
8. prove HEALTH cannot read/invoke TRANSPORT bootstrap surfaces and vice versa;
9. prove project roles have no direct DML on `PIPELINE_BOOTSTRAP` or `PIPELINE_CHECKPOINT`.

## Deliberate non-goals

This control plane does not standardize vendor-specific snapshot or CDC setup. SQL Server LSNs, database transaction snapshots, API cursors, Kafka offsets, and similar mechanisms are adapted by the source implementation into the generic handoff position only when the source can actually guarantee the declared semantics.
