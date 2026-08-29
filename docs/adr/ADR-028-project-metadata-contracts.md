# ADR-028 — Project, dataset, and RAW metadata contracts

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

Future Health, Transport, and new domains need a common way to declare stable technical behaviour without copying implementation logic or turning YAML into a second programming language.

The framework needs machine-validatable metadata before dbt environment resolution, reusable load strategies, CI/CD and reconciliation can be safely generalized.

## Decision

Define three versioned JSON Schema contracts in `enterprise-snowflake-data-project-framework`:

```text
project_schema/project.schema.json
project_schema/dataset.schema.json
project_schema/raw_contract.schema.json
```

### Project metadata

Contains only project identity/ownership metadata:

```text
schema_version
project.code
project.name
project.repository
project.owner_team
```

### Dataset metadata

Contains stable technical processing metadata:

```text
id
owner_team
raw_contract
load_strategy
implementation
business_key
watermark_column
freshness
reconciliation
```

Approved `load_strategy` values remain:

```text
full_refresh
append_only
incremental_merge
scd2_snapshot
scd2_merge
scd2_stream_task
```

`implementation` is `standard` or `custom`. `custom` is an escape hatch for genuine domain differences, not an exemption from testing/reconciliation/observability.

### RAW contract metadata

Defines the stable ingestion/downstream boundary:

```text
source_system
entity
grain
business_key
source_timestamp
columns + types/nullability/classification
change_semantics
cadence
retention_days
breaking_change_policy
```

## Validation

The framework validator performs both JSON Schema validation and limited cross-field/reference checks, including:

- project/dataset/contract shape and allowed vocabulary;
- unique dataset ids;
- referenced RAW contract exists inside the project root;
- keyed incremental/SCD2 strategies require a dataset business key;
- freshness warning threshold cannot exceed error threshold;
- RAW business-key/source-timestamp fields must exist in declared columns;
- CDC operation/sequence columns must be present and declared;
- duplicate RAW column names are rejected.

## Non-goals

Metadata does **not** encode:

- business joins;
- metric formulas;
- domain calculations;
- arbitrary SQL expressions;
- branching orchestration programs.

Those remain explicit SQL/code.

## Consequences

- project onboarding gets a stable validation contract before broader dbt implementation;
- framework features can consume predictable metadata without domain-specific copy/paste;
- schema versions make future breaking metadata changes explicit;
- semantic validation stays intentionally narrow and technical rather than becoming an orchestration engine.
