# ADR-035 — Silver correctness and SCD consumer contract

- **Status:** Accepted — Hybrid Framework v2
- **Revised:** 2026-09-09

## Decision

Silver is the **data correctness layer**. It owns grain, canonical typing, deduplication, business keys, interpretation of landed change evidence, current state, SCD1, SCD2, deletes, deterministic ordering, idempotency, late-arriving data, and authoritative history.

Gold is the **business derivation layer**. It owns business joins, KPI logic, aggregation, marts, reporting entities, and semantic preparation.

The Framework begins after source-faithful data exists in Bronze. It does not operate source connectors and does not own SQL Server LSNs, Kafka offsets, API cursors, file-discovery state, or similar ingestion progress.

## SCD2

An SCD2 entity publishes one authoritative history implementation:

```text
SILVER_CANONICAL.<ENTITY>_HISTORY
  -> historical consumers
  -> <ENTITY>_CURRENT view
       -> GOLD
```

The history contract preserves:

```text
valid_from
valid_to
is_current
version_order
```

and deterministic source ordering, delete/tombstone semantics present in landed evidence, replay/idempotency, reinsert behavior, and late-arrival correction.

Gold should consume `<ENTITY>_CURRENT`; it should not duplicate `where is_current = true` in every mart.

The correctness-first Framework implementation may rebuild deterministic history from retained landed event evidence. Any future affected-key optimization must prove identical invariants and behavior before replacing that path.

SCD2 is a `load.strategy`. It is intentionally independent from `materialization.type` and `runtime.mode`; names such as `scd2_merge` and `scd2_stream_task` are superseded combination vocabulary.

## SCD1

SCD1 remains current-state semantics. Readable domain SQL resolves the intended source row when necessary; the reusable stateful materialization performs keyed upsert and contract-defined tombstone/delete handling.

SCD1 is likewise independent from whether the model is invoked by dbt, a Task, another Snowflake-managed runtime, or a custom runtime.

## Source fidelity

A downstream consumer cannot invent history fidelity that the landed Bronze evidence does not contain.

The landed-data contract therefore remains separate from downstream dataset maintenance metadata and records properties such as:

```text
change semantics
capture fidelity
ordering columns
idempotency key
delete semantics
```

Those fields describe evidence already available to processing. They do not make the Framework responsible for source acquisition.

## Processing bootstrap

`PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP` governs the transition from an already-landed Bronze baseline to steady-state **processing** checkpoint state. It is not a connector bootstrap controller.

Any source-side snapshot/CDC handoff must first be made safe by the ingestion implementation. The processing bootstrap may record a landed boundary only after that evidence exists in Snowflake and is suitable for downstream reconciliation.

## Consequences

- Silver is the single source of truth for entity correctness/history;
- Gold does not own SCD mechanics;
- source connector technology can change without redesigning Silver, provided the landed contract remains compatible;
- Framework checkpoints and bootstrap state are processing state, not copies of connector-owned progress.
