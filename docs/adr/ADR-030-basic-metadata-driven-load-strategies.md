# ADR-030 — Hybrid Dataset Metadata v2

## Status

Superseded and replaced — 2026-09-09

The previous combined load-strategy API is intentionally removed. There is no compatibility mapping.

## Decision

Dataset execution metadata has three orthogonal axes:

```yaml
load:
  strategy: scd2
materialization:
  type: table
runtime:
  mode: dbt
```

`load.strategy` describes maintenance semantics only:

```text
full_refresh
append_only
incremental_merge
scd1
scd2
custom
```

`materialization.type` describes the Snowflake/dbt object:

```text
table
view
dynamic_table
snapshot
custom
```

`runtime.mode` describes who runs it:

```text
dbt
snowflake_managed
task
stream_task
external
custom
```

Names that combine these concerns, such as `scd2_stream_task` or `scd2_merge`, are not part of the architecture.

## Boundary

Metadata is technical configuration, not a SQL DSL. JOIN, CASE, filters, GROUP BY, window functions and business expressions remain in readable domain SQL.

The Framework may translate bounded technical configuration into dbt materialization config, query tags, control-plane calls, DQ and stateful correctness mechanics. It must not generate domain transformations.

## Custom

`custom` is first-class on each axis. A custom dataset can still reuse deployment, query tags, run registration, config snapshots, DQ, reconciliation, RBAC and reset lifecycle while keeping its business implementation domain-owned.

## Verification

Framework CI validates schema v2, parses/compiles a mixed-strategy project, runs focused SCD correctness behavior tests and performs static Snowflake/security contract checks. Live Snowflake execution is a separate WIF acceptance gate and is not inferred from static CI.
