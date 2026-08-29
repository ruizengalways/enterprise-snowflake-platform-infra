# Canonical Repository Directory Layout

> **Status:** Accepted architecture plan / implemented paths where noted.
>
> **Scope:** All five Enterprise Snowflake repositories.
>
> **Rule:** Create directories with real content only; no `.gitkeep` theatre.

## 1. Principles

1. Repository boundaries come before folder convenience.
2. One concern has one authoritative location.
3. Project repos stay thin; generic mechanics live in framework/platform repos.
4. Reusable workflows live under `.github/workflows/`.
5. Terraform uses reusable modules + explicit lifecycle/state roots.
6. Bootstrap identities are separate from routine infrastructure.
7. Remote-state cloud choice is an adapter, not domain logic.
8. Metadata describes stable technical behaviour, not business-programming logic.

## 2. `enterprise-snowflake-platform-infra`

```text
enterprise-snowflake-platform-infra/
├── README.md
├── .terraform-version
├── docs/
│   ├── CURRENT_CONTEXT.md
│   ├── PROJECT_BLUEPRINT.md
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

Rules:

- `organization/` is ORGADMIN-only account lifecycle.
- `identity/<env>/` creates platform Terraform identity/WIF.
- routine `dev/uat/prod` own stable account/domain infrastructure.
- `project-identity/dev` runs after `platform/dev` and creates project PR-CI service users bound to existing `AR_<DOMAIN>_CI` roles.
- `workspace-access` owns stable DEV personal/CI permission boundaries, not individual PR schemas.
- employee membership comes from IdP/SCIM, not Terraform user records.
- backend is selected at runtime (`azurerm` or `s3`).
- state/credentials/real secret-bearing tfvars are never committed.

## 3. `enterprise-snowflake-data-project-framework`

Implemented/current:

```text
enterprise-snowflake-data-project-framework/
├── README.md
├── pyproject.toml
├── src/enterprise_snowflake_framework/
│   ├── __init__.py
│   ├── workspaces.py
│   ├── query_tags.py
│   └── metadata_validation.py
├── project_schema/
│   ├── project.schema.json
│   ├── dataset.schema.json
│   └── raw_contract.schema.json
├── validation/
│   └── validate_metadata.py
├── scripts/
│   ├── render_workspace_sql.py
│   └── render_query_tag.py
├── examples/minimal-project/
│   ├── config/project.yml
│   ├── config/datasets/patient.yml
│   └── contracts/raw/patient.yml
├── tests/
│   ├── test_workspaces.py
│   ├── test_query_tags.py
│   └── test_metadata_validation.py
├── docs/patterns/
│   └── workspaces-and-query-tags.md
└── .github/workflows/
    ├── framework-ci.yml
    └── pr-workspace.yml
```

Target growth:

```text
dbt_package/
├── macros/environment/
├── macros/loading/{full_refresh,append_only,incremental_merge}/
├── macros/scd2/{snapshot,merge,stream_task}/
├── macros/reconciliation/
├── macros/freshness/
├── macros/audit/
└── tests/generic/

.github/workflows/
├── pr-ci.yml
├── deploy-dev.yml
├── promote-uat.yml
├── promote-prod.yml
├── rollback-prod.yml
├── recover-data.yml
└── backfill.yml
```

Rules:

- framework owns generic technical mechanics, never domain business SQL;
- project/dataset/RAW schemas are versioned technical contracts;
- metadata validation remains narrow and does not become an orchestration DSL;
- projects pin framework workflow/code versions deliberately.

## 4. `enterprise-snowflake-health-analytics`

Current first workflow + target:

```text
enterprise-snowflake-health-analytics/
├── README.md
├── .github/workflows/
│   └── pr-workspace.yml                     # implemented, pinned framework caller
├── config/
│   ├── project.yml                          # next
│   ├── datasets/
│   ├── contracts/raw/
│   └── operations/
├── dbt/
│   ├── dbt_project.yml
│   ├── packages.yml
│   ├── models/{staging,intermediate,canonical,marts,semantic}/
│   ├── snapshots/
│   └── tests/{singular,domain}/
└── ingestion/openflow/                      # Phase 8 only
```

Health owns Health contracts/business SQL/tests. Generic workspace/metadata/load mechanics stay in framework.

## 5. `enterprise-snowflake-transport-analytics`

```text
enterprise-snowflake-transport-analytics/
├── README.md
├── .github/workflows/
│   └── pr-workspace.yml                     # implemented, pinned framework caller
├── config/
│   ├── project.yml                          # next
│   ├── datasets/
│   ├── contracts/raw/
│   └── operations/
├── dbt/
│   ├── dbt_project.yml
│   ├── packages.yml
│   ├── models/{staging,intermediate,canonical,marts,semantic}/
│   ├── snapshots/
│   └── tests/{singular,domain}/
└── ingestion/
    ├── snowpipe_streaming/                  # later
    └── kafka_connector/                     # later
```

Direct Snowpipe Streaming and Kafka Connector later target the same logical RAW event contract.

## 6. `enterprise-snowflake-demo-source-systems`

Target:

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

It represents systems outside Snowflake and stops at the source/RAW boundary.

## 7. Dependency direction

```text
platform-infra
    │ provisions accounts/RBAC/warehouses/identities
    ▼
health-analytics / transport-analytics
    ▲
    │ consume pinned framework code/workflows
    │
data-project-framework

source-systems
    │ external-style data/events
    ▼
RAW contract -> project downstream
```

## 8. Current next growth

```text
framework dbt environment/database/schema resolution
project metadata files validated by reusable framework tooling
thin PR CI -> DEV/UAT/PROD delivery contracts
basic approved load strategy implementation/tests
```

Still deferred:

```text
Kafka Connector
Snowpipe Streaming
Openflow
full governance policies
full observability dashboards
production rollback automation
```
