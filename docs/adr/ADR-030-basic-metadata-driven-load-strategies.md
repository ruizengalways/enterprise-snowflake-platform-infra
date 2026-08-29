# ADR-030 — Basic Metadata-Driven dbt Load Strategies

## Status

Accepted — 2026-08-29

## Context

The platform has an approved load-strategy vocabulary in dataset metadata:

```text
full_refresh
append_only
incremental_merge
scd2_snapshot
scd2_merge
scd2_stream_task
```

A project should not duplicate standard dbt materialization settings and unique-key configuration in every model when those technical choices are already declared in validated dataset metadata. At the same time, the framework must not infer business filters, joins, source predicates or late-arrival semantics that differ by dataset.

## Decision

The shared framework owns a bounded metadata-to-dbt bridge.

Validated project metadata is rendered into dbt vars before parse/run. A project model identifies the governed dataset, for example:

```jinja
{{ enterprise_snowflake_framework.esf_configure_dataset('vehicle_position') }}
```

The framework implements these **basic** standard strategies through `esf_configure_dataset()`:

### `full_refresh`

Maps to a dbt table materialization. The model query remains explicit project SQL.

### `append_only`

Maps to dbt incremental materialization with Snowflake incremental strategy `append`.

The basic macro does **not** invent a source watermark/checkpoint predicate. The rows returned by the model on an incremental invocation are the rows dbt appends. A dataset/source-specific extraction/window predicate therefore remains explicit unless the project is consuming one of the separately implemented framework capture/checkpoint primitives.

### `incremental_merge`

Maps to dbt incremental materialization with Snowflake incremental strategy `merge` and derives `unique_key` from validated `dataset.business_key` metadata. Composite business keys are retained as a list.

## Deliberately outside the basic macro

The following approved strategies deliberately fail compilation in the basic-load macro:

```text
scd2_snapshot
scd2_merge
scd2_stream_task
```

This does **not** mean SCD2 is unimplemented in the framework. SCD2 requires dedicated correctness-oriented macros and invariant tests and therefore must not silently degrade to a generic dbt incremental model.

A dataset with:

```yaml
implementation: custom
```

also fails the standard configuration macro. Custom implementation remains explicit project code while still participating in standard metadata, tests, observability and reconciliation contracts.

## Metadata bridge

`render_dbt_vars.py` validates the project tree first and exposes only bounded technical metadata under:

```text
esf_project
esf_datasets
```

It does not expose arbitrary SQL/business-rule fields because those fields do not belong in the metadata schema.

The reusable project dbt static-check action renders the same vars and passes them to offline `dbt parse`, ensuring checked-in project configuration and metadata are compatible.

## Verification

Framework CI uses dbt Core `1.12.3` and dbt-snowflake `1.12.0` and inspects the generated manifest to prove:

```text
full_refresh      -> materialized=table
append_only       -> materialized=incremental, incremental_strategy=append
incremental_merge -> materialized=incremental, incremental_strategy=merge, unique_key from metadata
```

This is configuration-level proof only. Live Snowflake execution, idempotency, performance and recovery behavior still require integration tests once DEV infrastructure exists.

## Consequences

Positive:

- dataset technical metadata becomes the source of truth for standard materialization behavior;
- project models remain explicit SQL rather than YAML-generated transformations;
- business keys are not duplicated between metadata and dbt config;
- unsupported SCD2/custom cases fail clearly rather than receiving a misleading default;
- future domains receive the same mechanics without copy/paste.

Trade-offs:

- the basic `append_only` materialization itself does not decide source extraction/checkpoint semantics;
- freshness/reconciliation/audit are separate framework/runtime concerns rather than hidden materialization hooks;
- SCD2 remains intentionally outside the basic macro because its correctness contract is materially richer.

## Implementation status — 2026-08-29

The broader framework has since implemented the separate primitives this ADR intentionally kept out of `esf_configure_dataset()`:

```text
capture archetype helpers
checkpoint read/advance helpers
pipeline run/check-result helpers
freshness/reconciliation helpers
SCD2 snapshot
SCD2 immutable-event affected-key rebuild
SCD2 Stream + Triggered Task
SCD2 invariants + deterministic behavior oracle
```

Therefore the durable boundary is **basic materialization helper vs dedicated runtime/SCD primitives**, not “implemented vs future”. See ADR-031 for capture archetypes and ADR-035 for SCD consumer semantics.
