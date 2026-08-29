# ADR-031 — Reusable Capture Archetypes and Dynamic Table Fallback

- Status: Accepted
- Date: 2026-08-29

## Context

Enterprise data projects repeatedly encounter the same source-capture shapes even when products and vendors differ: full snapshots, watermark extracts, lookback windows, tombstones, net CDC, full CDC, transaction logs, Kafka/Debezium, Delta CDF, business events, snapshot diff, API cursors and incremental files.

The framework must be reusable across companies without creating fourteen unrelated implementations or hiding source-specific business semantics inside YAML.

Dynamic Tables are useful for declarative transformations, but they are not the only production execution engine. Operational experience can require disabling them because of product defects, unsupported SQL, refresh/reinitialization behaviour, or poor incremental-refresh performance for a particular workload.

## Decision

### 1. Normalize source capture into six framework archetypes

The framework recognizes six technical archetypes:

1. `snapshot`
2. `watermark`
3. `net_change`
4. `full_change`
5. `snapshot_diff`
6. `cursor_or_file`

Source products map onto these archetypes. Product names such as SQL Server CDC, Debezium, Kafka or Delta CDF are source adapters, not framework execution models.

### 2. Separate source fidelity from target history

Every capture contract declares what the source can actually provide:

```text
current_state
net_change
full_change
full_event
```

Delete capability is separate:

```text
none
explicit_delete
tombstone
inferred_snapshot_diff
source_defined
```

The framework must not claim a stronger Silver history than the source fidelity supports.

Examples:

- watermark/current-state input can build reliable SCD1 but only observed-version SCD2;
- net CDC can build batch-level history but cannot reconstruct multiple changes that were collapsed inside the source CDC window;
- full CDC/event input can support complete ordered SCD2 when the ordering key is reliable;
- full snapshot can infer deletes only when consecutive snapshots are retained and compared.

### 3. Bronze is replayable evidence first, current projection second

For sources where history, delete inference, reconciliation, recovery or replay matter, the authoritative Bronze object is append/replayable evidence.

A full snapshot must therefore retain snapshot batches, for example:

```text
snapshot_id
snapshot_at
batch_id
ingested_at
record_hash
<business columns>
```

A current-state `MERGE`/replace table may exist as a projection, but it must not be the only copy when downstream SCD2 or snapshot-diff semantics are required.

For full CDC/events, the authoritative Bronze table is append-only source events. Snowflake Streams are consumers of this evidence, not substitutes for the evidence itself.

### 4. Classic Snowflake execution is the mandatory baseline

Every reusable framework primitive must have a non-Dynamic-Table production path based on Snowflake-native objects:

```text
regular TABLE
STREAM where useful
TASK / triggered TASK / task graph
MERGE / INSERT / DELETE
Snowflake Scripting where atomic multi-step logic is required
Time Travel / CLONE for recovery
```

The classic implementation is the portability and break-glass path.

### 5. Dynamic Table is an optional execution engine

Dynamic Tables can be supplied when the transformation is naturally declarative and performance is proven.

Rules:

- never make Dynamic Table the only supported implementation;
- prefer explicit `REFRESH_MODE` instead of relying on `AUTO` for production behaviour;
- use Dynamic Tables primarily for SELECT-defined current projections, filtering, joins and aggregations;
- use classic Streams/Tasks for procedural MERGE/delete logic, strict orchestration, explicit retry/checkpoint handling and workloads where Dynamic Table incremental refresh is unstable or expensive;
- do not treat a Stream on a Dynamic Table as full audit history;
- maintain equivalent contract tests for the classic and Dynamic Table implementations where both exist.

### 6. Retry/lookback/checkpoint state is explicit runtime state

Git remains the configuration source of truth. Mutable ingestion progress belongs in runtime control state, not project YAML.

Reusable control state includes concepts such as:

```text
pipeline/dataset
last_successful_watermark
last_successful_cursor
last_source_sequence
last_snapshot_id
last_file_identity
last_successful_batch_id
updated_at
```

The authoritative runtime tables live under the account `PLATFORM_CONTROL` lifecycle when the implementation is introduced.

### 7. Idempotency is source-specific but contract-driven

The framework supports bounded technical parameters, not arbitrary orchestration expressions.

Typical idempotency identities:

```text
watermark/current rows    -> business key + source version/timestamp
net CDC                   -> source position + business key
full CDC / transaction log-> LSN/SCN/sequence/event id
Kafka/Debezium            -> topic + partition + offset
Delta CDF                 -> commit version + row identity
business event            -> event id or source offset
snapshot                  -> snapshot id + business key
file                      -> file path/content key + row number or source key
API                       -> cursor + business/event key
```

## Canonical mapping

| Source shape | Archetype | Authoritative Bronze | Delete fidelity | SCD1 | SCD2 fidelity |
|---|---|---|---|---|---|
| Full snapshot | snapshot | append snapshot batches | inferred by diff | yes | snapshot-grain |
| Incremental watermark | watermark | append observed versions or merge current + retained evidence | normally none | yes | observed changes only |
| Watermark + lookback | watermark | same, with overlap dedupe | normally none | yes | observed changes only |
| Watermark + tombstone | net_change | append observations/tombstones, optional current projection | explicit tombstone | yes | observed changes |
| Native CDC net changes | net_change | append each capture batch before current merge | explicit delete | yes | batch/net history |
| Native CDC full changes | full_change | append ordered CDC events | explicit delete | yes | full when ordering reliable |
| Transaction log CDC | full_change | append log events | explicit delete | yes | full when ordering reliable |
| Debezium/Kafka CDC | full_change | append ordered events | explicit/source defined | yes | full when ordering reliable |
| Delta CDF | full_change | append commit changes | explicit/source defined | yes | full when commit ordering reliable |
| Business event source | full_change | append immutable events | source defined | yes | full event history |
| Snapshot diff | snapshot_diff | append snapshots + derived diff | inferred | yes | snapshot-grain |
| API cursor | cursor_or_file | append response evidence/events; optional current merge | API defined | yes | API dependent |
| Incremental files | cursor_or_file | append file rows + file metadata | source/file dependent | yes | file-content dependent |

## Consequences

### Positive

- a new company selects a small capture archetype instead of cloning bespoke pipelines;
- downstream design is independent of SQL Server/Kafka/Delta/API/file transport choice;
- source fidelity limits are explicit and testable;
- Dynamic Table problems do not force a platform rewrite;
- replay/recovery and delete inference remain possible because Bronze evidence is retained;
- full CDC history is not accidentally destroyed by merging too early.

### Trade-offs

- replayable Bronze can consume more storage than current-state-only tables;
- snapshot sources require retention policy and snapshot identifiers;
- classic and Dynamic Table dual implementations increase framework test surface;
- some source-specific checkpoint and ordering details remain explicit project configuration by design.

## Implementation direction

Framework growth should add:

```text
capture contract/schema + semantic validation
Bronze append/current projection primitives
snapshot diff primitive
watermark/lookback dedupe primitive
net-change merge primitive
full-change ordered event primitive
SCD1 consumer primitive
SCD2 snapshot/merge/stream-task implementations
classic + Dynamic Table compatibility tests
checkpoint/reconciliation/freshness/audit control primitives
```

Dynamic Tables remain optional throughout.