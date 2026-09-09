# Current Platform Context — Hybrid Framework v2

Updated: 2026-09-09

The enterprise Snowflake platform uses three Snowflake accounts for DEV, UAT and PROD, environment/domain databases, domain-scoped roles and workload warehouses, and a shared `PLATFORM_CONTROL` control plane.

## Data architecture boundary

```text
External sources -> ingestion -> BRONZE -> SILVER -> GOLD -> semantic
                               |<-- data processing Framework -->|
```

Ingestion tools are independent. The Framework does not operate source connectors or own connector checkpoints.

## Processing model

Silver is the data-correctness layer. Gold is the business-derivation layer. Dataset policy is table/dataset-scoped; a domain database can contain full refresh, append-only, incremental merge, SCD1, SCD2, Dynamic Table and custom datasets together.

Framework v2 uses three independent metadata axes: `load.strategy`, `materialization.type` and `runtime.mode`. The old combination strategy vocabulary is not supported.

## Compute

Domain metadata declares logical workloads such as `transform`. Environment configuration maps each domain workload to the physical warehouse through `projects.<domain>.warehouse_keys` and `warehouses`.

## Control plane

`PLATFORM_CONTROL` remains separate from Bronze/Silver/Gold and stores config snapshots, run/checkpoint state, bootstrap lifecycle, DQ/reconciliation, generation/reset and observability. Domain repos use guarded domain-scoped procedures/views rather than direct DML to shared base tables.

## Portability

Transport and Health standalone synthetic cores remain independent of Framework, PLATFORM_CONTROL, Terraform and enterprise workload identity.

## Acceptance status

Static Terraform/control SQL contracts exist. Live Snowflake acceptance must be reported only after the relevant DEV/WIF workflow has actually executed successfully.
