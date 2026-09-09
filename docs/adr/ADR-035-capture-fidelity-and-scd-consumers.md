# ADR-035 — Silver Correctness and SCD Consumer Contract

- **Status:** Replaced — 2026-09-09

## Decision

Silver is the **data correctness layer**. It owns grain, canonical typing, deduplication, business keys, CDC interpretation, current state, SCD1, SCD2, deletes, deterministic ordering, idempotency, late-arriving data and authoritative history.

Gold is the **business derivation layer**. It owns business joins, KPI logic, aggregation, marts, reporting entities and semantic preparation.

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

and deterministic source ordering, delete/tombstone semantics, replay/idempotency, reinsert behavior and late-arrival correction. Gold should consume `<ENTITY>_CURRENT`; it should not duplicate `where is_current = true` in every mart.

The correctness-first Framework implementation may rebuild deterministic history from retained event evidence. Any future affected-key optimization must prove identical invariants and behavior before replacing that path.

## SCD1

SCD1 remains current-state semantics. Readable domain SQL resolves the intended source row when necessary; the reusable stateful materialization performs keyed upsert and source-contract tombstone deletes.

## Source fidelity

A downstream consumer cannot invent history fidelity that the landed source evidence does not contain. Raw/source contracts therefore remain separate from downstream dataset maintenance metadata.
