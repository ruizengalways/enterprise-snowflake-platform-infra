# Canonical Repository Directory Layout

> **Status:** Accepted architecture.
>
> **Scope:** All five Enterprise Snowflake repositories.
>
> **Rule:** Create directories only with real content; no `.gitkeep` theatre.

This document defines ownership and significant paths. It is intentionally **not** an exhaustive file inventory; exhaustive inventories become stale as implementation grows. The repository tree is the authority for individual implementation files.

## 1. Principles

1. Repository boundaries come before folder convenience.
2. One concern has one authoritative location.
3. Project repos stay thin; generic technical mechanics live in framework/platform repos.
4. Reusable workflows/actions live under `.github/`.
5. Terraform uses reusable modules + explicit lifecycle/state roots.
6. Bootstrap identities are separate from routine infrastructure.
7. Remote-state cloud choice is an adapter, not Snowflake/domain logic.
8. Metadata describes bounded technical behaviour, not business-programming logic.
9. Project model SQL is environment-agnostic and uses `ref()` / `source()`.
10. Planned directories appear only when the first real implementation file exists.
11. Volatile release SHAs belong in project pins and `CURRENT_CONTEXT.md`, not in this layout standard.

## 2. `enterprise-snowflake-platform-infra`

Significant structure:

```text
enterprise-snowflake-platform-infra/
├── README.md
├── docs/
│   ├── CURRENT_CONTEXT.md
│   ├── PROJECT_BLUEPRINT.md
│   ├── architecture/
│   ├── adr/
│   ├── standards/
│   └── runbooks/
├── config/
│   ├── organization.yml
│   └── environments/{dev,uat,prod}.yml
├── terraform/
│   ├── README.md
│   ├── backend-profiles/{azurerm,s3}/
│   ├── scripts/select-backend.sh
│   ├── modules/
│   │   ├── analytics-environment/
│   │   ├── warehouse/
│   │   ├── rbac/
│   │   ├── workspace-access/
│   │   ├── platform-control/
│   │   ├── workload-identity/
│   │   └── service-identity/
│   └── stacks/
│       ├── organization/
│       ├── identity/{dev,uat,prod}/
│       ├── {dev,uat,prod}/
│       └── project-identity/{dev,uat,prod}/
├── snowflake/
│   ├── control/
│   └── monitoring/
└── .github/workflows/
```

Ownership:

- `organization/` is ORGADMIN-only account lifecycle;
- `identity/<env>/` owns platform Terraform service user/WIF bootstrap;
- routine `{dev,uat,prod}/` roots own stable account/domain infrastructure;
- `project-identity/<env>/` owns project workload service users/WIF bindings after platform roles exist;
- `workspace-access` owns stable DEV personal/CI permission boundaries, not individual ephemeral schemas;
- `snowflake/control/` owns native operational SQL inside the Terraform-created `PLATFORM_CONTROL` structural boundary;
- employee membership comes from IdP/SCIM, not Terraform user records;
- remote backend is selected at runtime (`azurerm` or `s3`);
- Terraform state/credentials/secret-bearing tfvars are never committed.

Ten lifecycle/state roots exist: organization, three platform identities, three routine platform states and three project-identity states.

## 3. `enterprise-snowflake-data-project-framework`

Significant structure:

```text
enterprise-snowflake-data-project-framework/
├── README.md
├── pyproject.toml
├── requirements-dbt.txt
├── src/enterprise_snowflake_framework/
├── project_schema/
├── validation/
├── scripts/
├── dbt_package/
│   ├── dbt_project.yml
│   ├── macros/
│   └── tests/
├── examples/
├── tests/
├── docs/patterns/
└── .github/
    ├── actions/
    │   ├── validate-metadata/
    │   └── dbt-static-check/
    └── workflows/
        ├── framework-ci.yml
        ├── pr-workspace.yml
        └── project-deploy.yml
```

Implemented shared behavior includes:

```text
personal/PR workspace naming + guarded SQL
canonical QUERY_TAG construction
project/dataset/RAW metadata schemas + semantic validation
dbt physical target/context resolution
validated metadata -> dbt vars
basic full_refresh / append_only / incremental_merge configuration
capture/checkpoint/runtime-quality primitives
SCD1 and SCD2 snapshot/merge/stream-task primitives
SCD2 invariant tests + deterministic behavior oracle
Snowflake-native Stream/Task/Dynamic Table helpers
reusable metadata/dbt static CI
reusable PR workspace lifecycle
reusable immutable project deployment
```

Rules:

- generic technical mechanics belong here; domain business SQL never does;
- metadata remains a bounded technical contract, not an orchestration DSL;
- `implementation: custom` stays available for genuine project differences;
- projects pin framework revisions deliberately;
- workflow security invariants are tested in framework CI.

Remaining framework growth is driven by live verification and real consumers, especially rollback/backfill/recovery automation and later ingestion-specific adapters. Do not create speculative directories.

## 4. `enterprise-snowflake-health-analytics`

Significant structure:

```text
enterprise-snowflake-health-analytics/
├── README.md
├── config/
├── contracts/raw/
├── dbt/
└── .github/workflows/
    ├── metadata-ci.yml
    ├── dbt-static-ci.yml
    ├── pr-workspace.yml
    └── deploy.yml
```

Health owns its RAW contracts, dataset metadata and business SQL/tests/semantics. Generic environment, capture, SCD, quality, workspace and deployment mechanics remain in the framework.

The first Health `patient` contract is full-change CDC feeding `scd2_merge`; it is not a snapshot source.

## 5. `enterprise-snowflake-transport-analytics`

Significant structure:

```text
enterprise-snowflake-transport-analytics/
├── README.md
├── config/
├── contracts/raw/
├── dbt/
└── .github/workflows/
    ├── metadata-ci.yml
    ├── dbt-static-ci.yml
    ├── pr-workspace.yml
    └── deploy.yml
```

Transport owns its event contract and business transformations. Direct Snowpipe Streaming and Kafka Connector remain deferred; both must later converge on the same logical RAW contract.

Do not create ingestion directories until implementation begins.

## 6. `enterprise-snowflake-demo-source-systems`

This repository represents systems outside the Snowflake platform. Add implementation paths only when real source simulation begins.

Expected responsibility areas may include:

```text
logical Health/Transport source generators
source mutations/scenarios
REST/SSE/GTFS-realtime adapters
file/SQL-source simulators
Kafka producer
Snowpipe Streaming producer
integration tests
```

It must not contain dbt transformations, canonical models, marts, Semantic Views or downstream platform reconciliation logic.

## 7. Dependency direction

```text
platform-infra
    │ provisions accounts/RBAC/warehouses/identities
    ▼
health-analytics / transport-analytics
    ▲
    │ consume immutable framework revision
    │
data-project-framework

source-systems
    │ external-style records/events
    ▼
project RAW contract -> project downstream
```

Rules:

- framework never imports project business code;
- platform infra never owns domain transformation models;
- source simulator never depends on downstream analytics;
- Health and Transport do not call each other directly.

## 8. Current growth boundary

Already implemented in source/static CI:

```text
dbt target/context resolution
metadata/RAW contracts and validation
query tags
capture/checkpoint/quality primitives
SCD1/SCD2 reusable mechanics and invariants
PR workspace lifecycle
stable immutable deployment workflow
project CI/deployment WIF identity roots
```

Still deliberately deferred until live DEV proof:

```text
Kafka Connector
Direct Snowpipe Streaming
Openflow
full rollback/backfill automation
full observability dashboards
advanced governance policy rollout
```

For the current exact release SHA, verified CI runs and blockers, read `docs/CURRENT_CONTEXT.md` rather than encoding those volatile facts here.
