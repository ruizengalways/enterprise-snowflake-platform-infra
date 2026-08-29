# Pipeline Pattern Coverage Audit

## Purpose

This document records how the Enterprise Snowflake reference platform maps to the pipeline-design patterns in:

- `ruizengalways/data-engineering-cheetsheet/README.md`
- `ruizengalways/data-engineering-cheetsheet/docs/pipeline-design-walkthrough.md`

Audit date: **2026-08-29**.

The cheatsheet's core model is:

```text
data semantics
  -> capture / delivery
  -> cursor / checkpoint
  -> Bronze meaning
  -> Silver meaning
  -> fidelity / recovery
```

The platform uses the same reasoning model but keeps its canonical physical-layer vocabulary:

```text
external source
  -> project-owned RAW contract
  -> STAGING
  -> INTERMEDIATE / CANONICAL
  -> MARTS
  -> SEMANTIC
```

`Bronze`, `Silver`, and `Gold` in the cheatsheet describe **semantic responsibilities**, not additional Snowflake schemas in this platform.

## Audit basis and version boundary

Health and Transport currently pin executable framework release:

```text
b1896aa110632e94c21010695ee000c9181d9caf
```

At the time of this audit, framework `main` is four commits ahead of that revision and the diff contains documentation files only. Therefore the implementation coverage below applies to the project-pinned executable framework revision as well as current framework `main`.

No item in this document should be interpreted as live Snowflake proof. Real remote state, Snowflake account bootstrap, WIF execution, external source ingestion and live runtime testing remain pending.

## Status vocabulary

```text
READY
  Required framework contract and reusable Snowflake/dbt primitives exist in source/static CI.
  A source adapter or project SQL can still be required because source/business semantics are intentionally explicit.

PARTIAL
  The pattern is representable, but an important reusable contract/runtime piece is still missing or ambiguous.

GAP
  Current v1 framework contracts cannot safely represent the case without a design/code change.

BY DESIGN
  The remaining implementation is intentionally project/domain-specific and should not become generic framework YAML/code.
```

A `READY` pattern is still **not live-proven** until the DEV control plane and real source path exist.

# 1. Cheatsheet 14-pattern coverage

| # | Cheatsheet pattern | Platform mapping | Framework status | Current boundary |
|---:|---|---|---|---|
| 1 | Full Snapshot -> Current Bronze | `snapshot` + `current_state`; current projection / `full_refresh` | **PARTIAL** | Snapshot semantics are supported, but v1 metadata does not explicitly declare `current-only RAW` versus retained snapshot evidence. The platform allows a current projection, but overwrite-only RAW must not be the only copy when delete inference, replay, reconciliation or SCD2 history is required. |
| 2 | Full Snapshot -> Snapshot Bronze | `snapshot` + `current_state` + `snapshot_id` | **READY** | Retained complete snapshot batches, `esf_snapshot_diff()`, current projection and `esf_scd2_snapshot_apply_sql()` exist. Source extraction itself remains adapter-specific. |
| 3 | Watermark -> Current Bronze | `watermark` + `current_state` + checkpoint + current MERGE | **READY** | Contract/checkpoint/latest-observation/MERGE pieces exist. Source predicate/extraction remains explicit. End-to-end runtime is currently blocked by the domain-scoped `PLATFORM_CONTROL` access gap. |
| 4 | Watermark + Lookback -> Current Bronze | `watermark` + `lookback_minutes` + latest-by-key + current MERGE | **READY** | Lookback metadata and deterministic ordering exist. The extractor must calculate/read the overlap window and checkpoint advancement must occur only after successful processing. |
| 5 | Watermark + Lookback -> Raw Append Bronze | append RAW observations + `watermark` + `lookback_minutes` + idempotency | **READY** | `append_only`, checkpoint helpers, `esf_latest_observation()` and current MERGE primitives compose this pattern. APPEND preserves observations received; it does not create unseen source history. |
| 6 | Watermark + Soft Delete -> Current Bronze | current-state watermark row containing delete state | **PARTIAL** | This remains **watermark/current-state semantics**, not net-change merely because the row is called a tombstone. v1 metadata lacks a first-class `soft_delete_column/value` contract and therefore project SQL must currently interpret the delete flag explicitly. |
| 7 | Watermark + Lookback + Soft Delete -> Raw Append Bronze | append current-state observations + lookback + explicit soft-delete interpretation | **PARTIAL** | Lookback/idempotency/current-projection pieces exist, but soft-delete-row semantics are not yet first-class metadata. Source tombstone retention versus recovery window is also not explicitly modeled. |
| 8 | Net Changes -> Current Bronze | `net_change` + `net_change` fidelity + ordered/deduped MERGE | **READY** | Net-change evidence and explicit delete operation can feed `esf_merge_current_state_sql()`. History guarantee is only net-window fidelity. |
| 9 | Net Changes -> Append Bronze | append net-window evidence | **READY** | `net_change` capture plus append evidence and deterministic identity are supported. Downstream current/SCD history cannot claim full-change fidelity. |
| 10 | Full / All Changes -> Event Bronze | `full_change` + `full_change` fidelity + immutable event RAW | **READY** | Ordering/idempotency metadata, append-only Streams, Triggered Tasks, current projection and full-change SCD2 consumers exist. Generic consumer assumes each non-delete event carries enough state to build the requested projection; before/after-image capability is not yet explicit metadata. |
| 11 | Full Changes -> Current Bronze (lossy) | full-change event input -> ordered latest/current projection | **READY** | `esf_latest_observation()` / Dynamic Table current projection + MERGE can intentionally collapse history. The reference design prefers retaining immutable event RAW first when replay/audit may matter. |
| 12 | Business Events | `full_change` archetype + `full_event` fidelity | **READY / BY DESIGN** | Capture, ordering, idempotency and event-driven Snowflake execution are reusable. Converting domain events into a canonical business-event contract or entity state remains explicit project SQL because it is business semantics. |
| 13 | Snapshot Diff -> Current | `snapshot_diff` + `net_change` fidelity -> MERGE current | **READY** | `esf_snapshot_diff()` derives I/U/D from complete comparable snapshots and can feed the current MERGE path. |
| 14 | Snapshot Diff -> Append Changes | retained snapshots -> derived append diff | **READY** | The diff primitive exists and the derived changes can be appended as replayable evidence before downstream current/SCD consumers. Fidelity remains snapshot-grain. |

## Overall result

The platform can represent all fourteen cheatsheet patterns at the architecture level.

Reusable framework primitives are already sufficient for **10 of the 14 patterns** without a new generic abstraction. Four patterns are intentionally marked `PARTIAL` because the remaining gaps are semantically important rather than cosmetic:

```text
1. current-only RAW versus retained RAW evidence is not a v1 metadata field
6. watermark + soft-delete row is not first-class delete metadata
7. watermark + lookback + soft-delete row has the same delete-contract gap
10. full-change before/after/reconstructible-state capability is not explicit metadata
```

Pattern 10 is still executable for full-state/post-image event contracts; the limitation matters when a source emits partial update deltas or image semantics that require source-specific reconstruction.

# 2. Important semantic corrections from the audit

## 2.1 Soft-delete row is not automatically net change

The cheatsheet correctly distinguishes:

```text
current-state row
  id=300, is_deleted=true
  -> watermark/current-state semantics

change-feed event
  position=5001, DELETE, id=300
  -> net_change or full_change semantics depending on the feed
```

The platform must preserve this distinction.

Do **not** classify a watermark-delivered soft-delete row as `net_change` merely because documentation uses the word `tombstone`.

## 2.2 Cursor and event identity are separate

The current contract already models this correctly:

```text
capture.checkpoint_kind
  = where to continue

capture.idempotency_columns
  = what exact version/event was processed

capture.ordering_columns
  = source order when order matters
```

Examples:

```text
watermark / rowversion
LSN / SCN / source position
Kafka partition + offset
API cursor
file identity
```

A checkpoint value is not assumed to be a unique event identifier.

## 2.3 RAW APPEND does not imply full source fidelity

A watermark source can append every extraction observation and still only provide `current_state` fidelity.

Likewise:

```text
net_change append history != full change history
snapshot history          != intermediate event history
```

The framework's separate `capture.archetype` and `capture.fidelity` fields are the correct boundary and should be retained.

## 2.4 CDC time and business effective time are different

`esf_scd2_event_history_select()` accepts an explicit `effective_at_column` plus deterministic `order_columns`, so project SQL can use a business-effective timestamp when that is the actual SCD contract.

However, v1 metadata does not label timestamps as:

```text
capture/change time
business effective time
```

That distinction therefore remains an explicit project/SCD design responsibility rather than something the framework should infer.

# 3. Orthogonal production concerns

The cheatsheet correctly treats these as requirements around the pattern rather than separate pattern rows.

| Concern | Current status | Assessment |
|---|---|---|
| Safe initial load / snapshot-to-incremental handoff at position `P` | **GAP** | No reusable bootstrap/handoff contract or runbook yet guarantees snapshot baseline + change position without gap/double-apply. This should be added before a real CDC adapter is considered production-ready. |
| At-least-once/redelivery idempotency | **READY / project-aware** | `idempotency_columns`, ordering metadata and SCD retry-safe behavior exist. Non-SCD event/current projections may still need explicit project/source dedupe SQL because event identity semantics differ by source. |
| Source ordering | **READY** | `ordering_columns` and full-change validator requirements exist; SCD event history consumes deterministic order. |
| Cursor != event identity | **READY** | Checkpoint and idempotency fields are separate. |
| Physical delete with plain watermark | **SUPPORTED AS A LIMITATION** | Framework documentation must continue to state that plain watermark cannot make physical deletes authoritative without soft-delete rows, delete feed or periodic complete reconciliation. |
| Soft-delete row vs delete event | **PARTIAL** | Semantic distinction is now documented, but v1 metadata does not have a dedicated soft-delete-row contract. |
| Reliable business/entity key | **GAP FOR KEYLESS SOURCES** | `raw_contract.schema.json` requires at least one non-null `business_key`. Truly keyless snapshots/logs cannot be onboarded without inventing a key, which is prohibited. A future keyless-source design is required if such a source becomes a real consumer. |
| Before/after image capability | **PARTIAL** | RAW columns can carry images, but v1 capture metadata does not state `after_only`, `before_and_after`, `delta_only`, etc. Generic SCD/current projection must not assume unavailable images. |
| Business-effective SCD2 | **PARTIAL / BY DESIGN** | SCD macro supports explicit effective timestamp/order. The framework does not infer business-effective semantics from CDC/change time. |
| Reconciliation | **PARTIAL** | Current reusable metrics cover row count, distinct business key and min/max source timestamp. PK presence diff, aggregate/hash bundles and periodic snapshot drift checks are not yet generic primitives. |
| Schema evolution | **PARTIAL** | RAW contract has `breaking_change_policy`, but there is no automated contract-version diff or `EXPAND -> MIGRATE -> CONTRACT` workflow yet. |
| Recovery / replay | **PARTIAL** | Architecture uses retained RAW evidence, Snowflake Time Travel/CLONE and deterministic downstream rebuild principles, but reusable backfill/replay/repair workflow templates are not implemented yet. |
| Source retention vs recovery window | **PARTIAL** | RAW `retention_days` exists, but source-side CDC/tombstone/Kafka/API retention and the required enterprise recovery window are not yet a first-class validated contract. |
| Runtime checkpoint/run/check authorization | **BLOCKER** | `PLATFORM_CONTROL` tables/procedures exist, but domain-scoped project runtime access is not safely implemented. See `OPERATIONAL_CONTROL_ACCESS.md`. |
| External ingestion adapters | **NOT IMPLEMENTED YET** | Kafka Connector, direct Snowpipe Streaming, Openflow and real DB/API/file adapters remain intentionally deferred until the DEV control plane is proven. |
| Live Snowflake behavior | **NOT PROVEN YET** | Static/source CI does not prove WIF, privileges, concurrency, performance, task/stream behavior or recovery in a real account. |

# 4. What should not be over-abstracted

The audit does **not** justify turning every cheatsheet axis into another metadata field.

Keep these explicit until repeated real consumers prove a reusable contract is necessary:

```text
source extraction SQL/API calls
business-event canonicalization
business-effective-time rules
source-specific before/after reconstruction
source-specific bootstrap query/transaction mechanics
source-specific schema migrations
```

Likewise, do not add a `Bronze/Silver/Gold` physical schema taxonomy. The platform already has a stable RAW/downstream layer model.

A future metadata field should be added only when it changes reusable technical behavior and can be validated consistently across domains.

# 5. Near-term framework gaps revealed by this audit

Before broad ingestion demos, the most valuable reusable additions are:

```text
1. domain-scoped PLATFORM_CONTROL operational access
2. safe initial-load / position-P handoff pattern for incremental/CDC sources
3. explicit soft-delete-row contract when a real watermark source needs it
4. keyless-source contract only when a real source proves the need
5. before/after/reconstructible-state capability if a real CDC source requires it
6. contract-version compatibility + expand/migrate/contract guidance/tooling
7. broader reconciliation primitives
8. replay/backfill/recovery workflow templates
```

Items 3-5 should not be added speculatively as a large generic DSL. Implement the smallest contract required by an actual Health/Transport/source-adapter use case.

# 6. Live acceptance gate for a pattern

A pattern is not production-proven until DEV demonstrates:

```text
source/bootstrap correctness
checkpoint/cursor recovery
retry/redelivery idempotency
source ordering correctness
delete behavior
reconciliation/drift detection
schema-change behavior
failure/replay recovery
domain-isolated operational state
cost/query-tag attribution
least-privilege execution identity
```

Only after those gates should the same immutable code revision be promoted through UAT and PROD.

## Related platform documents

- `docs/CURRENT_CONTEXT.md`
- `docs/PROJECT_BLUEPRINT.md`
- `docs/architecture/OPERATIONAL_CONTROL_ACCESS.md`
- `docs/architecture/RBAC_MODEL.md`
- `docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`
- `docs/adr/ADR-031-capture-archetypes-and-dynamic-table-fallback.md`
- `docs/adr/ADR-035-capture-fidelity-and-scd-consumers.md`

## Related framework documents

- `enterprise-snowflake-data-project-framework/docs/patterns/capture-archetypes.md`
- `enterprise-snowflake-data-project-framework/docs/patterns/source-capture-matrix.md`
- `enterprise-snowflake-data-project-framework/docs/patterns/scd-consumers.md`
- `enterprise-snowflake-data-project-framework/docs/patterns/snowflake-native-first.md`
