# Canonical Repository Directory Layout

> **Status:** Accepted architecture / current implemented paths where noted.
>
> **Scope:** All five Enterprise Snowflake repositories.
>
> **Rule:** Create directories only with real content; no `.gitkeep` theatre.

## 1. Principles

1. Repository boundaries come before folder convenience.
2. One concern has one authoritative location.
3. Project repos stay thin; generic mechanics live in framework/platform repos.
4. Reusable workflows/actions live under `.github/`.
5. Terraform uses reusable modules + explicit lifecycle/state roots.
6. Bootstrap identities are separate from routine infrastructure.
7. Remote-state cloud choice is an adapter, not Snowflake/domain logic.
8. Metadata describes stable technical behaviour, not business-programming logic.
9. Project model SQL is environment-agnostic and should use `ref()` / `source()`.
10. Planned directories appear only when the first real implementation file exists.

## 2. `enterprise-snowflake-platform-infra`

Current structure:

```text
enterprise-snowflake-platform-infra/
├── README.md
├── .terraform-version
├── docs/
│   ├── CURRENT_CONTEXT.md                   # new-session handoff; read first
│   ├── PROJECT_BLUEPRINT.md                 # long-term canonical architecture
│   ├── architecture/
│   │   ├── REPOSITORY_LAYOUT.md
│   │   ├── ACCOUNT_TOPOLOGY.md
│   │   ├── RBAC_MODEL.md
│   │   └── TERRAFORM_STATE_AND_IDENTITY.md
│   ├── adr/ADR-*.md
│   ├── standards/
│   │   ├── NAMING_CONVENTIONS.md
│   │   ├── TERRAFORM_STANDARDS.md
│   │   └── COST_ATTRIBUTION.md
│   └── runbooks/
│       └── terraform-platform-bootstrap.md
├── config/
│   ├── organization.yml
│   └── environments/{dev,uat,prod}.yml
├── terraform/
│   ├── README.md
│   ├── backend-profiles/{azurerm,s3}/backend.tf
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
│       ├── dev/
│       ├── project-identity/dev/
│       ├── uat/
│       └── prod/
├── snowflake/
│   └── monitoring/queries/cost_attribution.sql
└── .github/workflows/
    ├── terraform-ci.yml
    └── terraform-plan-dev.yml
```

Ownership:

- `organization/` is ORGADMIN-only account lifecycle.
- `identity/<env>/` owns platform Terraform service user/WIF.
- routine `dev/uat/prod` own stable account/domain infrastructure.
- `project-identity/dev` runs after `platform/dev` and owns PR-CI service users bound to existing `AR_<DOMAIN>_CI` roles.
- `workspace-access` owns stable DEV personal/CI workspace permission boundaries, not individual ephemeral schemas.
- employee membership comes from IdP/SCIM, not Terraform user records.
- remote backend is selected at runtime (`azurerm` or `s3`).
- Terraform state/credentials/secret-bearing tfvars are never committed.

## 3. `enterprise-snowflake-data-project-framework`

Current implemented baseline:

```text
enterprise-snowflake-data-project-framework/
├── README.md
├── pyproject.toml
├── requirements-dbt.txt
├── src/enterprise_snowflake_framework/
│   ├── __init__.py
│   ├── workspaces.py
│   ├── query_tags.py
│   ├── metadata_validation.py
│   ├── targets.py
│   └── dbt_vars.py
├── project_schema/
│   ├── project.schema.json
│   ├── dataset.schema.json
│   └── raw_contract.schema.json
├── validation/
│   └── validate_metadata.py
├── scripts/
│   ├── render_workspace_sql.py
│   ├── render_query_tag.py
│   ├── resolve_dbt_target.py
│   ├── render_dbt_vars.py
│   └── assert_dbt_manifest.py
├── dbt_package/
│   ├── dbt_project.yml
│   └── macros/
│       ├── environment/targets.sql
│       └── loading/strategies.sql
├── examples/
│   ├── minimal-project/
│   └── dbt-smoke/
├── tests/
│   ├── test_workspaces.py
│   ├── test_query_tags.py
│   ├── test_metadata_validation.py
│   ├── test_targets.py
│   └── test_dbt_vars.py
├── docs/patterns/
│   └── workspaces-and-query-tags.md
└── .github/
    ├── actions/
    │   ├── validate-metadata/action.yml
    │   └── dbt-static-check/action.yml
    └── workflows/
        ├── framework-ci.yml
        └── pr-workspace.yml
```

Implemented shared behavior now includes:

```text
personal/PR workspace naming + guarded SQL
canonical JSON QUERY_TAG construction
project/dataset/RAW metadata schemas + validation
dbt physical database/schema/warehouse target resolution
validated metadata -> dbt vars rendering
basic full_refresh / append_only / incremental_merge dbt configuration
reusable metadata and offline dbt static CI
reusable PR workspace lifecycle
```

Next framework growth is real capability, not placeholder directories:

```text
query-tag/dbt lifecycle integration
reconciliation/freshness/audit primitives
checkpoint/watermark helper where semantics can genuinely be common
scd2 snapshot/merge/stream-task implementations + invariant tests
DEV deployment workflow/identity contract
UAT/PROD promotion workflow/identity contract
rollback/recovery/backfill workflow templates
```

Rules:

- generic technical mechanics belong here; domain business SQL never does;
- metadata remains a bounded technical contract, not an orchestration DSL;
- `implementation: custom` stays available for genuine project differences;
- projects pin framework revisions deliberately.

## 4. `enterprise-snowflake-health-analytics`

Current implemented shell:

```text
enterprise-snowflake-health-analytics/
├── README.md
├── config/
│   ├── project.yml
│   └── datasets/patient.yml
├── contracts/
│   └── raw/patient.yml
├── dbt/
│   ├── dbt_project.yml
│   ├── packages.yml
│   ├── profiles.yml
│   └── macros/target_wrappers.sql
└── .github/workflows/
    ├── metadata-ci.yml
    ├── dbt-static-ci.yml
    └── pr-workspace.yml
```

Health owns Health contracts, future source declarations/models/tests/business rules/semantics. Generic environment/load/workspace/metadata mechanics remain in the framework.

Add `models/`, `snapshots/`, tests and later Openflow only when their first real implementations are created.

## 5. `enterprise-snowflake-transport-analytics`

Current implemented shell:

```text
enterprise-snowflake-transport-analytics/
├── README.md
├── config/
│   ├── project.yml
│   └── datasets/vehicle_position.yml
├── contracts/
│   └── raw/vehicle_position.yml
├── dbt/
│   ├── dbt_project.yml
│   ├── packages.yml
│   ├── profiles.yml
│   └── macros/target_wrappers.sql
└── .github/workflows/
    ├── metadata-ci.yml
    ├── dbt-static-ci.yml
    └── pr-workspace.yml
```

Transport owns its event contract and future business transformations. Direct Snowpipe Streaming and Kafka Connector remain deferred; both must later converge on the same logical RAW contract.

Do not create ingestion directories until implementation begins.

## 6. `enterprise-snowflake-demo-source-systems`

Target when source implementation begins:

```text
enterprise-snowflake-demo-source-systems/
├── README.md
├── pyproject.toml
├── sources/{health,transport}/
├── adapters/{rest,sse,gtfs_realtime}/
├── sinks/{files,sql_server,snowflake_direct,snowpipe_streaming,kafka}/
├── scenarios/{normal,late_arriving,out_of_order,duplicates,deletes,bad_data,source_outage,schema_change,volume_spike}/
├── config/{health,transport}/
└── tests/{unit,integration}/
```

It represents systems outside Snowflake and stops at the project-owned RAW boundary.

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

## 8. Current next growth

Completed since the earlier layout plan:

```text
dbt target resolution                      ✅
project metadata/RAW contracts              ✅
reusable metadata validation                ✅
offline project dbt parse                    ✅
basic standard load configuration            ✅
```

Next:

```text
QUERY_TAG integration into dbt lifecycle
reconciliation/freshness/audit primitives
checkpoint/watermark helper
SCD2 implementations + invariant tests
thin DEV/UAT/PROD project-delivery contracts
```

Still deliberately deferred:

```text
Kafka Connector
Snowpipe Streaming
Openflow
full governance policies
full observability dashboards
production rollback automation
```
