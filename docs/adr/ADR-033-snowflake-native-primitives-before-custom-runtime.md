# ADR-033 — Prefer Snowflake Native Primitives Before Custom Runtime

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

The platform needs reusable CDC, scheduling, runtime observability, freshness and data-quality behavior. Reimplementing capabilities already owned by Snowflake would create duplicate state, ambiguous ownership and more failure modes.

Examples of state Snowflake already owns include Stream offsets, Task retry/execution history, Dynamic Table refresh state and Data Metric Function results.

## Decision

Use Snowflake-native capabilities first when they provide the required semantics.

Priority:

```text
Snowflake GA/native capability
  -> thin framework wrapper where naming/guardrails help
  -> explicit project SQL for real source/domain differences
  -> custom platform runtime state only when no suitable Snowflake primitive exists
```

Preview features are not the default production baseline unless explicitly accepted.

### CDC

For Snowflake-internal table CDC:

- standard Stream for INSERT/UPDATE/DELETE change consumption;
- append-only Stream for immutable insert-only event/landing tables;
- one Stream per independent consumer;
- Snowflake owns the Stream offset;
- no `PLATFORM_CONTROL` checkpoint mirrors a Stream offset.

Routine deployment must not silently recreate offset-bearing Streams. Source-object or append-only changes are explicit migrations with replay/offset decisions.

Within one explicit transaction, repeated reads of a Stream see the same change set. SCD2 Stream consumers should use this native repeatable-read behavior instead of introducing a shared affected-key work table solely to preserve the current Stream batch.

Snapshot diff remains only for upstream interfaces that genuinely provide snapshots and cannot expose preserved change data.

### Triggered execution

Use Triggered Tasks with `SYSTEM$STREAM_HAS_DATA` for Stream-driven processing.

Use Snowflake task controls for retry, timeout, suspend-after-failure and overlap policy instead of building a second scheduler.

### Task run state

For Snowflake Task-driven pipelines, authoritative execution state is Snowflake task metadata/history, including `TASK_HISTORY` and `COMPLETE_TASK_GRAPHS`.

Do not duplicate every Task run into `PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN`.

`PIPELINE_RUN` remains valid for externally orchestrated runs such as GitHub/dbt deployment execution or external-source extraction.

### Current-state / SCD1

For declarative current-state transformations over append-preserved change/event data, prefer a Snowflake Dynamic Table. Window-based latest-row selection is the native baseline when it expresses the required semantics.

The platform default for incrementalizable Dynamic Table projections is `ADAPTIVE`; projects may explicitly use `INCREMENTAL` or `FULL` when justified. `AUTO` is not the production reference default because it leaves the resolved mode implicit.

Classic MERGE remains a fallback for procedural current-state behavior that cannot be represented cleanly as a Dynamic Table SELECT.

### SCD2 history

Use Streams + Tasks for SCD Type 2 history. Snowflake's current Dynamic Table decision guide distinguishes SCD2 history from current-state use cases and recommends Streams and Tasks for SCD2.

The framework therefore does not provide an SCD2 Dynamic Table wrapper. It keeps only the necessary interval/history transformation SQL and delegates Stream offset, triggering, retry, transaction commit and Task run history to Snowflake.

### Data quality

On Snowflake Enterprise Edition, use system Data Metric Functions and Expectations for supported standard metrics such as freshness, row count and uniqueness.

Framework SQL may declare schedules/associations and query native references/results, but Snowflake owns metric execution and result state. DMF association DDL is deployment/migration configuration, not a model hook that is blindly re-run on every dbt invocation. Inspect `DATA_METRIC_FUNCTION_REFERENCES` / `DATA_METRIC_FUNCTION_EXPECTATIONS` for drift.

Snowflake `FRESHNESS` without a timestamp argument measures time since the table was last modified. Timestamp-column freshness has supported timestamp type requirements; do not change a domain RAW timestamp type merely to fit the system DMF. Source-event freshness that cannot be represented by the system DMF remains an explicit SQL fallback.

Cross-table/cross-system reconciliation remains explicit SQL when system DMFs do not directly express the required comparison.

## Consequences

Positive:

- fewer duplicated control tables, work tables and procedures;
- less custom state to recover;
- clearer lifecycle ownership;
- native Snowflake monitoring is directly usable;
- simpler operational troubleshooting;
- current-state and history patterns follow Snowflake's own product guidance.

Trade-offs:

- some capabilities, especially Data Quality Monitoring, depend on Snowflake edition;
- native object semantics and retention limits must be understood;
- explicit fallback SQL is still required for unsupported source semantics and cross-system reconciliation;
- changing a Stream source/mode or DMF association remains a governed migration rather than a generic idempotent model operation.
