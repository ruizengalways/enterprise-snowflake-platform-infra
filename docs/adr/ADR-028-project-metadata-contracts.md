# ADR-028 — Project, dataset, and landed-data metadata contracts

- **Status:** Accepted — revised for Hybrid Framework v2 on 2026-09-09
- **Original date:** 2026-08-29

## Context

Health, Transport, and future domains need a common way to declare stable technical processing behaviour without copying implementation logic or turning YAML into a second programming language.

Hybrid Framework v2 also makes the ownership boundary explicit:

```text
External source -> ingestion -> BRONZE | SILVER -> GOLD -> semantic
                                      ^ Framework processing boundary
```

Source acquisition technology and connector progress such as SQL Server LSNs, Kafka offsets, API cursors, file-discovery state, or Openflow runtime state are not Framework metadata and are not Framework checkpoints.

## Decision

The Framework owns three machine-validatable JSON Schema contracts:

```text
project_schema/project.schema.json
project_schema/dataset.schema.json
project_schema/raw_contract.schema.json
```

All current contracts require:

```text
schema_version: 2
```

Schema v1 is superseded and is not a compatibility contract for new project work.

### Project metadata

Project metadata contains project identity and ownership only:

```text
project.code
project.name
project.repository
project.owner_team
```

### Dataset metadata

Dataset metadata answers **how the landed data is processed**. The three principal axes are orthogonal:

```text
load.strategy
materialization.type
runtime.mode
```

Current load strategies are:

```text
full_refresh
append_only
incremental_merge
scd1
scd2
custom
```

Current materialization types are:

```text
table
view
dynamic_table
snapshot
custom
```

Current runtime modes are:

```text
dbt
snowflake_managed
task
stream_task
external
custom
```

Do not recombine those axes into names such as `scd2_merge` or `scd2_stream_task`.

Dataset metadata may also contain bounded technical configuration such as:

```text
business key
watermark column used by downstream processing
SCD2 effective/order/tracked/delete semantics
logical compute workload
freshness
reconciliation measures
```

`custom` is a first-class escape hatch for genuinely different technical behavior. It is not an exemption from observability, quality, deployment, config-snapshot, or reset controls where those contracts still apply.

### Landed-data / Bronze contract

The file remains named `raw_contract.schema.json` for repository compatibility, but its architectural meaning is the contract for source-faithful data already landed in Bronze.

It declares properties of the evidence downstream processing can rely on, including:

```text
source_system
entity
grain
business_key
source_timestamp
columns + types/nullability/classification
change_semantics: snapshot | append | cdc
capture_fidelity: current_state | net_change | full_change | full_event
ordering_columns
idempotency_key
breaking_change_policy
```

The contract can describe delete/tombstone semantics present in the landed data. It does not operate the source connector and does not store where the connector should resume.

## Validation

The Framework validator performs JSON Schema validation plus bounded cross-field/reference checks, including:

- project/dataset/contract shape and allowed vocabulary;
- `schema_version == 2`;
- unique dataset ids;
- referenced landed-data contract exists inside the project root;
- keyed incremental/SCD strategies require a business key;
- SCD2 requires explicit effective time, deterministic order, tracked columns, and late-arrival policy;
- freshness warning threshold cannot exceed error threshold;
- declared key/timestamp/operation/order/idempotency columns must exist where required;
- duplicate contract column names are rejected.

## Non-goals

Metadata does **not** encode:

- source extraction SQL/API calls;
- connector LSN/offset/cursor state;
- business joins or metric formulas;
- arbitrary SQL expressions;
- domain calculations;
- branching orchestration programs.

Those remain in the system that owns them.

## Consequences

- a domain database may mix full refresh, incremental merge, SCD1, SCD2, Dynamic Tables, Tasks, and custom datasets without creating separate control systems;
- Framework behavior stays metadata-driven without becoming a YAML programming language;
- ingestion can change technology without forcing downstream metadata redesign, provided the landed Bronze contract remains compatible;
- breaking metadata changes are explicit through schema versions rather than silent compatibility assumptions.
