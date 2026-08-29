# ADR-035 — Capture Fidelity and Reusable SCD Consumers

- **Status:** Accepted
- **Date:** 2026-08-29
- **Builds on:** ADR-031 — Reusable Capture Archetypes and Dynamic Table Fallback

## Context

Enterprise source systems expose materially different change fidelity: full snapshots, timestamp watermarks, lookback windows, tombstones, net CDC, full transaction-log changes, event streams, API cursors and file increments.

ADR-031 defines the bounded capture archetypes and the rule that classic Snowflake implementations remain available when Dynamic Tables are unsuitable. This decision defines how reusable SCD consumers interpret those capture contracts.

The framework must not pretend that every source can provide complete delete detection or transaction-level history. Source fidelity is the upper bound on downstream history fidelity.

## Decision

Preserve familiar source/capture scenarios for onboarding, but implement the bounded capture archetypes defined by ADR-031:

```text
snapshot
watermark
net_change
full_change
snapshot_diff
cursor_or_file
```

RAW contracts separately declare capture fidelity:

```text
current_state
net_change
full_change
full_event
```

Source fidelity is authoritative. A downstream implementation cannot claim history that was already collapsed upstream.

SCD is a consumer of the capture contract:

- SCD1 first reduces each processing window to one deterministic row per business key before MERGE.
- snapshot SCD2 uses transactional close + insert and can infer deletes only at snapshot granularity.
- full-change/full-event SCD2 retains immutable event history and uses correctness-first affected-key history rebuild.
- low-latency full-change/full-event SCD2 may use an append-only Stream + Triggered Task; Stream consumption and history replacement occur in one transaction.
- metadata validation rejects structurally invalid combinations such as `scd2_snapshot` over a `full_change` capture contract or `scd2_stream_task` over current-state/net-change fidelity.

Dynamic Table SCD projections are optional wrappers only. Every supported Dynamic Table path retains a classic regular-table implementation. Production Dynamic Table refresh mode is explicit; the framework does not default to `AUTO`.

## RAW preservation rules

A full snapshot cannot use destructive overwrite as its only authoritative RAW evidence when delete inference, SCD2, replay, reconciliation or audit is required. Preserve snapshot batches with snapshot/batch identity, then derive current-state or diff projections.

Full-change/full-event capture writes immutable events to a regular Snowflake table before any Stream consumer. A Stream is an offset/delta consumer, not the system of record for complete CDC history.

## Runtime state

Git stores capture configuration. Mutable checkpoint/source-position/cursor/snapshot/file progress lives in `PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT` and advances only after successful target processing.

Snowflake-owned Stream offsets are not duplicated into a custom offset ledger.

## Correctness contract

Reusable SCD2 targets enforce these invariants:

```text
at most one current row per business key
valid non-negative version ranges
no overlapping history ranges
unique deterministic version ordinal per business key
```

The framework includes a deterministic SQL behavioral oracle covering duplicate replay, no-op same state, updates, delete/reinsert gaps, late events, ordering ties and equal-timestamp versions. Static CI proves parse/render/discovery; live Snowflake execution remains a DEV verification gate.

## Consequences

- A new domain selects a bounded capture contract rather than implementing source mechanics from scratch.
- Source limitations remain visible in metadata and CI.
- Late/out-of-order full-change events can repair history by recomputing only affected business keys from immutable evidence.
- Classic table/Stream/Task/MERGE/Snowflake-Scripting implementations remain the reliability baseline.
- Dynamic Tables can be adopted where benchmarked and operationally acceptable without redesigning the contract.
- High-volume projects may introduce optimized SCD2 fast paths only after proving the same invariants as the correctness-first implementation.
