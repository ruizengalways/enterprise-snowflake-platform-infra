# ADR-033 — Prefer Snowflake Native Primitives Before Custom Runtime

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

The platform needs reusable CDC, scheduling, runtime observability, freshness and data-quality behavior. Reimplementing capabilities already owned by Snowflake would create duplicate state, ambiguous ownership and more failure modes.

Examples of state Snowflake already owns include Stream offsets, Task retry/execution history and Data Metric Function results.

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

Snapshot diff remains only for upstream interfaces that genuinely provide snapshots and cannot expose preserved change data.

### Triggered execution

Use Triggered Tasks with `SYSTEM$STREAM_HAS_DATA` for Stream-driven processing.

Use Snowflake task controls for retry, timeout, suspend-after-failure and overlap policy instead of building a second scheduler.

### Task run state

For Snowflake Task-driven pipelines, authoritative execution state is Snowflake task metadata/history, including `TASK_HISTORY` and `COMPLETE_TASK_GRAPHS`.

Do not duplicate every Task run into `PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN`.

`PIPELINE_RUN` remains valid for externally orchestrated runs such as GitHub/dbt deployment execution or external-source extraction.

### Data quality

On Snowflake Enterprise Edition, use system Data Metric Functions and Expectations for standard supported metrics such as freshness, row count and uniqueness.

Framework SQL may declare schedules/associations and query native results, but Snowflake owns metric execution and result state.

Cross-table/cross-system reconciliation remains explicit SQL when system DMFs do not directly express the required comparison.

### SCD

Snowflake provides CDC, scheduling, transactions and task monitoring, but not a single native SCD2 object that replaces history interval logic for all source semantics.

The framework therefore keeps only the necessary SCD transformation SQL while delegating offsets, triggering, retry and execution history to Snowflake.

## Consequences

Positive:

- fewer duplicated control tables and procedures;
- less custom state to recover;
- clearer lifecycle ownership;
- native Snowflake monitoring is directly usable;
- simpler operational troubleshooting.

Trade-offs:

- some capabilities, especially Data Quality Monitoring, depend on Snowflake edition;
- native object semantics and retention limits must be understood;
- explicit fallback SQL is still required for unsupported source semantics and cross-system reconciliation.
