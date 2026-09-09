# Processing Bootstrap Handoff Control Plane

## Status

Source/static implementation and DEV deployment wiring exist on `main`. Live DEV WIF, Snowflake authorization, concurrency, and end-to-end data behavior are not yet proven.

## Purpose

`PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP` governs the one-time transition from an **already-landed Bronze baseline** to normal checkpoint-driven downstream processing.

It does not operate source connectors and does not own source progress such as SQL Server LSNs, Kafka offsets, API cursors, file-discovery state, or Openflow runtime state.

The Framework macro contract says the same thing:

```text
already-landed Bronze data
  -> processing bootstrap
  -> downstream processing checkpoint
```

## Ownership

```text
ingestion implementation
  owns source-side consistency, extraction, connector progress, and landing

landed-data / Bronze contract
  describes the source-faithful evidence available to processing

PLATFORM_CONTROL
  owns mutable processing-bootstrap lifecycle and processing checkpoint commit

Framework
  owns bounded validation and domain-scoped call generation
```

A source-specific snapshot-to-CDC handoff may still be required, but it must be made safe by the ingestion implementation before downstream processing relies on the landed evidence. Do not put source extraction SQL, connector LSN/offset/cursor ownership, or business payloads in `PLATFORM_CONTROL`.

## State machine

The existing persisted states remain:

```text
BOUNDARY_CAPTURED
    -> SNAPSHOT_LANDED
    -> SNAPSHOT_VALIDATED
    -> HANDOFF_COMMITTED
```

`BOUNDARY_CAPTURED` means a **processing boundary over landed evidence** has been recorded. The value may be derived from a landed batch/version/sequence that downstream processing can use deterministically. It is not automatically the source connector's own resume token.

Each transition is performed through an owner-rights procedure whose project and environment are fixed in generated SQL.

A repeated call with already-recorded state is treated as an idempotent retry where persisted lifecycle state proves the operation already completed. Conflicting boundary metadata, snapshot identity, or reconciliation evidence fails closed. A caller cannot skip a state or mutate a committed handoff boundary.

`SNAPSHOT_VALIDATED` requires both an explicit `reconciliation_passed = TRUE` outcome and non-null reconciliation details. Structured details are audit evidence, not the authorization signal. JSON that merely says `status=PASS` is not sufficient, and `FALSE`/`NULL` is rejected.

## Initial-processing checkpoint guards

This state machine is only for a dataset's initial handoff into steady-state processing for the current generation.

`PIPELINE_BOOTSTRAP_START` rejects a dataset/checkpoint kind that already has a current-generation `PIPELINE_CHECKPOINT`. Re-seeding an already-running processing dataset uses the generation-aware reset lifecycle rather than silently reusing initial bootstrap.

At final commit the procedure checks again. If an existing processing checkpoint differs from the recorded landed boundary, handoff fails instead of overwriting it. This prevents a delayed bootstrap from rewinding already-progressed processing state.

## Atomic handoff invariant

The final procedure is the authorization and transaction boundary:

```text
SNAPSHOT_VALIDATED
  -> validate processing checkpoint is absent or equals landed handoff position
  -> BEGIN TRANSACTION
       MERGE current-generation PIPELINE_CHECKPOINT = landed handoff position
       UPDATE bootstrap STATUS = HANDOFF_COMMITTED
       COMMIT
     on transaction-block error:
       ROLLBACK + re-raise
```

Precondition failures occur outside the transaction-scoped exception handler. This prevents a partial state where downstream processing advances before the landed baseline has passed reconciliation.

## Generation awareness

Bootstrap and checkpoints are generation-aware. After a processing reset advances a dataset from generation N to N+1, old bootstrap/checkpoint evidence is retained for audit while the new generation begins without current processing state.

The new generation may then bootstrap from the preserved Bronze evidence and create its own processing checkpoint.

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

The generated view filters project and environment. Procedures embed those values server-side and expose neither `P_PROJECT_CODE` nor `P_ENVIRONMENT`.

## Single-writer assumption

The current baseline assumes one logical bootstrap writer per domain/dataset/generation lifecycle. Snowflake standard-table primary-key declarations are not treated as a substitute for runtime coordination.

Static CI proves fail-closed state transitions, domain-fixed SQL, generation routing, and atomic transaction shape. Live DEV must still test concurrent retry behavior before production approval.

## Live DEV acceptance criteria

A processing bootstrap is not considered proven until DEV demonstrates all of the following:

1. ingestion lands a deterministic Bronze baseline without delegating connector ownership to the Framework;
2. record a processing boundary over that landed evidence;
3. prove the landed baseline is complete/consistent enough for the declared downstream contract;
4. produce explicit reconciliation evidence and prove `FALSE` cannot advance validation;
5. reject handoff commit before validation;
6. reject bootstrap when a current-generation processing checkpoint already exists;
7. reject a final handoff that conflicts with a different processing checkpoint;
8. atomically commit checkpoint plus `HANDOFF_COMMITTED` after validation;
9. resume downstream processing with the declared inclusive/exclusive processing-boundary semantics;
10. retry every lifecycle step without uncontrolled double-apply;
11. prove HEALTH cannot read/invoke TRANSPORT bootstrap surfaces and vice versa;
12. prove project roles have no direct DML on `PIPELINE_BOOTSTRAP` or `PIPELINE_CHECKPOINT`.

## Deliberate non-goals

This control plane does not standardize vendor-specific source bootstrap mechanics. Database snapshots, source transaction positions, SQL Server LSNs, Kafka offsets, API cursors, and similar connector concerns remain ingestion-owned.

If ingestion needs to persist or recover those values, it must do so in the ingestion system or an explicitly ingestion-owned control surface rather than overloading Framework processing checkpoints.
