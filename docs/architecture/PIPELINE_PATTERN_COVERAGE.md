# Pipeline Pattern Coverage — Hybrid Framework v2

## Purpose

This document explains how common snapshot, incremental, CDC and event patterns map to the **v2 ownership boundary**.

The first question is no longer “which Framework capture archetype should own this source?” The correct sequence is:

```text
source semantics
  -> source/connector delivery capability
  -> landed BRONZE evidence and fidelity
  -> downstream load/history semantics
  -> materialization/runtime choice
  -> recovery proof
```

The Framework starts after Bronze is landed. Source connector checkpoints, source extraction predicates and source-side bootstrap consistency are ingestion concerns.

## Status vocabulary

```text
READY DOWNSTREAM
  The raw/source contract and Framework v2 can safely express/consume the landed evidence.
  Source ingestion may still need source-specific implementation.

INGESTION RESPONSIBILITY
  The hard part is extracting/delivering the source correctly; do not move it into Framework metadata.

BY DESIGN
  Business/source-specific transformation remains explicit SQL/code.

LIVE GATE
  Source/static contracts exist, but real Snowflake/WIF/runtime behavior is not yet proven.
```

No status below is a claim of live production readiness.

## 1. Pattern matrix

| Source/delivery pattern | Safe Bronze evidence | Downstream v2 use | Boundary/status |
| --- | --- | --- | --- |
| Full snapshot, current-only use | Complete landed snapshot/current table | `full_refresh`, SCD1/current projection if history is not required | READY DOWNSTREAM; source snapshot consistency is ingestion-owned |
| Retained complete snapshots | Immutable snapshot batches with snapshot identity/time | snapshot comparison, reconciliation, custom/SCD logic where complete snapshots are sufficient | READY DOWNSTREAM; retention policy must preserve required replay window |
| Watermark/current-state extraction | Latest observations for rows the source returns | current projection, `incremental_merge`, SCD1 where deletes are represented | READY DOWNSTREAM; source watermark and overlap query are ingestion-owned |
| Watermark + lookback | Replayed observations with deterministic identity/order | dedupe/latest-row SQL then current-state maintenance | READY DOWNSTREAM; overlap calculation/checkpoint belongs to ingestion unless downstream owns a landed-data boundary |
| Watermark + soft-delete row | Current-state rows including an explicit retained delete flag | readable project SQL interprets the source flag; SCD1/current target can delete/mark state | READY DOWNSTREAM / BY DESIGN; a soft-delete row is not a CDC delete event |
| Net-change CDC | Ordered change evidence, possibly only final change per source interval | current-state application; limited history only to the fidelity actually delivered | READY DOWNSTREAM; do not claim full event history |
| Full-change CDC | Append-preserved ordered changes including delete events | SCD1 or event-history SCD2; replay and late-arrival correction when identity/order are deterministic | READY DOWNSTREAM; Transport is the reference SCD2 case |
| Business events | Immutable domain events | append/event marts or explicit state projection | READY DOWNSTREAM / BY DESIGN; event-to-business-state meaning remains domain SQL |
| Snapshot diff | Complete comparable snapshots retained long enough to derive I/U/D | explicit diff SQL can feed current or append change evidence | BY DESIGN; do not pretend inferred diff has finer fidelity than snapshot cadence |
| API cursor / file feed | Landed rows/files with deterministic source identity and ordering where needed | append/current/custom downstream processing | READY DOWNSTREAM; API cursor/file discovery and retry state are ingestion-owned |
| Kafka / streaming events | Append-preserved events in Bronze with partition/offset or equivalent event identity when exposed | append, current projection or SCD depending on delivered fidelity | READY DOWNSTREAM; Kafka Connector/source offsets are connector-owned |
| Snowflake table changes | Landed mutable/append Snowflake table | native Streams + Tasks where appropriate | READY DOWNSTREAM; Snowflake owns Stream offset and Task history |

## 2. Raw/source contract v2

The raw/source contract describes the **evidence contract**, not connector implementation.

Relevant fields include:

```text
source_system
entity
grain
business_key
columns
source_timestamp
change_semantics.mode = snapshot | append | cdc
operation_column / sequence_column / delete semantics when applicable
capture_fidelity
ordering_columns
idempotency_key
cadence
retention_days
breaking_change_policy
```

It intentionally does **not** contain:

```text
SQL Server LSN checkpoint
Kafka consumer/connector offset state
API cursor state
connector retry schedule
source extraction query
source-side snapshot/CDC bootstrap transaction
Framework-owned connector archetype
```

Those belong to the source/ingestion implementation.

## 3. Fidelity rules

Downstream guarantees may never exceed the evidence delivered into Bronze.

```text
current-state observations
  cannot recreate unseen intermediate changes

net-change feed
  cannot claim full-change history

snapshot history
  cannot claim event-time changes between snapshots

full-change/full-event evidence
  can support event-history SCD only when ordering/idempotency are deterministic
```

For standard event-history SCD2, the Framework validator requires append-preserved `full_change` or `full_event` fidelity. If a source collapses changes before Bronze, use current-state semantics or an explicit project-specific design rather than inventing history.

## 4. Delete semantics

Keep these distinct:

```text
soft-delete current-state row
  id=300, is_deleted=true
  -> the source still returns a current observation carrying delete state

CDC delete/tombstone event
  position=5001, operation=DELETE, id=300
  -> ordered change evidence

physical delete with no delete evidence
  -> plain watermark/current-state extraction cannot make deletes authoritative
```

A downstream SCD/current model can only act on delete evidence that actually arrives. Periodic complete reconciliation or another authoritative delete feed is required when the source physically deletes rows without exposing delete state.

## 5. Ordering, identity and time

Three concepts are separate:

```text
source/connector continuation position
  where ingestion resumes

idempotency identity
  which exact landed event/version has already been processed

business/effective ordering
  how downstream state/history should be ordered
```

A Kafka offset or LSN may contribute to event identity/order, but it remains connector state when the connector owns continuation. The Framework raw contract may declare the landed ordering/idempotency columns required for downstream deterministic behavior without owning the connector checkpoint itself.

Likewise, CDC/change time and business-effective time are not automatically the same. Business-effective semantics remain explicit project design.

## 6. Downstream strategy mapping

Once Bronze evidence exists, dataset metadata chooses target behavior independently from acquisition technology:

```text
load.strategy
  full_refresh
  append_only
  incremental_merge
  scd1
  scd2
  custom

materialization.type
  table | view | dynamic_table | snapshot | custom

runtime.mode
  dbt | snowflake_managed | task | stream_task | external | custom
```

The same `full_change` Bronze contract could feed an append event table, SCD1 current state, SCD2 history or a custom business projection. Source fidelity and target semantics are related, but they are not one combined strategy name.

## 7. Snowflake-native state ownership

When Snowflake already owns execution state, use it directly:

```text
standard/append-only Stream
  -> Snowflake owns offset

Triggered Task
  -> Snowflake owns task scheduling/run history

Dynamic Table
  -> Snowflake owns refresh scheduling/state
```

Do not mirror Stream offsets or every Task execution into a second custom checkpoint/run ledger.

`PLATFORM_CONTROL` remains appropriate for project/external executions whose authoritative state is not already owned by a Snowflake native primitive, and for landed-data processing/bootstrap/reset/config audit boundaries.

## 8. Bootstrap boundary

There are two different handoffs:

```text
SOURCE/INGESTION HANDOFF
  consistent initial source snapshot + source CDC position
  -> ingestion responsibility

DOWNSTREAM LANDED-DATA HANDOFF
  already-landed Bronze baseline + downstream processing position
  -> Framework/PLATFORM_CONTROL may guard this
```

The v2 raw contract deliberately removed connector bootstrap/checkpoint fields. The Framework cannot prove a SQL Server snapshot-to-LSN or Kafka cutover that occurred outside Snowflake; the ingestion implementation must establish and test that boundary.

## 9. Recovery and reset

Recovery starts by identifying which evidence is authoritative.

If Bronze is valid but Silver/Gold state is wrong, generation-aware **processing reset** preserves Bronze and rebuilds downstream state.

Current reference reset contracts:

```text
Transport SCD2
  truncate SILVER_CANONICAL.VEHICLE_STATUS_HISTORY
  truncate SILVER_CANONICAL.VEHICLE_STATUS_HISTORY__ESF_EVENTS
  preserve BRONZE.VEHICLE_STATUS
  rebuild from landed evidence

Health SCD1
  truncate SILVER_CANONICAL.PATIENT
  preserve BRONZE.PATIENT
  rebuild from landed evidence
```

If Bronze itself is wrong or incomplete, use a separate ingestion-owned reland/source recovery procedure. Do not make a downstream reset silently delete source evidence.

## 10. Current source/static coverage

Available source/static building blocks include:

```text
schema-v2 project/dataset/raw validation
offline dbt parse/materialization routing
SCD1 current-state/tombstone primitive
SCD2 replay/delete/reinsert/late-arrival behavior oracle
SCD2 affected-key event-ledger implementation
Dynamic Table Gold routing
config snapshots
domain-scoped operational/bootstrap/reset/config APIs
generation-aware processing reset
framework-free Health/Transport source-contract fixtures
ordered Platform Control deployment bundle
```

The following previously documented blockers are no longer source/static gaps:

```text
domain-scoped PLATFORM_CONTROL API shape
Framework generation/reset primitives
domain processing-reset wrappers
ordered control-plane deployment bundle
raw contract v2 / orthogonal dataset strategy model
```

## 11. Intentional or remaining gaps

Do not fill these speculatively. Add the smallest reusable contract only when a real source proves the need.

```text
truly keyless standard source contracts
partial-update/before-after/delta reconstruction conventions
broader automated schema compatibility/evolution tooling
broader reconciliation/hash/drift bundles
generic repair/backfill/replay workflow templates
source-retention-vs-enterprise-recovery-window validation
real external ingestion adapters/runtime
```

Source-specific implementations such as SQL Server CDC extraction, Kafka Connector setup, direct Snowpipe Streaming producers, Openflow, REST API pagination and file discovery are intentionally outside the downstream Framework.

## 12. Live acceptance gate

A pattern is not production-proven until DEV demonstrates the parts that matter for that source and target:

```text
source delivery / initial cutover correctness
redelivery idempotency
ordering correctness
delete behavior
late-arrival behavior where relevant
reconciliation/drift checks
schema-change handling
failure/replay/recovery
least-privilege identity
domain-isolated control state
query-tag/cost attribution
processing reset where applicable
```

The platform-wide live gate is tracked by issue #6. Only after DEV is proven should the same immutable project SHA be promoted through UAT and PROD.

## 13. Reference implementations

```text
Health patient
  full-change CDC evidence
  -> readable latest-state SQL
  -> load.strategy=scd1

Transport vehicle_status
  full-change CDC evidence
  -> deterministic event SQL
  -> load.strategy=scd2
  -> history + current view

Transport vehicle_position
  append event evidence
  -> load.strategy=append_only

Transport depot_fleet_status
  current Silver view
  -> readable Gold aggregation SQL
  -> Dynamic Table / snowflake_managed
```

These examples prove mixed strategies can coexist in one governed domain/database without encoding source acquisition technology into the target strategy name.

## Related documents

- `docs/PROJECT_BLUEPRINT.md`
- `docs/CURRENT_CONTEXT.md`
- `docs/architecture/OPERATIONAL_CONTROL_ACCESS.md`
- `docs/architecture/DATASET_RESET_GENERATION.md`
- `docs/architecture/BOOTSTRAP_HANDOFF_CONTROL.md`
- Framework `docs/architecture/HYBRID_ARCHITECTURE_V2.md`
- Framework `docs/patterns/snowflake-native-first.md`
