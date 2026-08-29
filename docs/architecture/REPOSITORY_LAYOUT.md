# Canonical Repository Directory Layout

> **Status:** Accepted architecture plan / current implemented paths where noted.
>
> **Scope:** All five Enterprise Snowflake repositories.
>
> **Rule:** Create directories with real content only; no `.gitkeep` theatre.

## 1. Design principles

1. Repository boundaries come before folder convenience.
2. One concern has one authoritative location.
3. Health/Transport repos stay thin; shared mechanics belong in framework/platform repos.
4. Reusable GitHub workflows live under `.github/workflows/`.
5. Terraform uses reusable modules + isolated lifecycle roots.
6. Organization bootstrap, Terraform identity bootstrap and routine account infrastructure use separate state roots.
7. Remote-state cloud choice is an execution adapter, not Snowflake/domain logic.
8. Snowflake-native SQL is separated from dbt/model lifecycle.
9. Config contains non-secret metadata, never credentials.

## 2. `enterprise-snowflake-platform-infra`

Current/target structure:

```text
enterprise-snowflake-platform-infra/
├── README.md
├── .terraform-version
├── docs/
│   ├── CURRENT_CONTEXT.md                    # fast new-session handoff
│   ├── PROJECT_BLUEPRINT.md                  # canonical long-term architecture
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
│   ├── backend-profiles/
│   │   ├── azurerm/backend.tf
│   │   └── s3/backend.tf
│   ├── scripts/select-backend.sh
│   ├── modules/
│   │   ├── analytics-environment/
│   │   ├── warehouse/
│   │   ├── rbac/
│   │   ├── workspace-access/
│   │   ├── platform-control/
│   │   └── workload-identity/
│   └── stacks/
│       ├── organization/
│       ├── identity/{dev,uat,prod}/
│       ├── dev/
│       ├── uat/
│       └── prod/
├── snowflake/
│   └── monitoring/queries/cost_attribution.sql
└── .github/workflows/
    ├── terraform-ci.yml
    └── terraform-plan-dev.yml
```

Later real capabilities may add native SQL under `snowflake/control`, `governance`, `alerts`, `recovery`; do not create placeholders before they have content.

### Platform Infra ownership rules

- `organization/` is the only ORGADMIN Terraform root.
- `identity/<env>/` owns platform Terraform service user/WIF/`AR_TERRAFORM_<ENV>`.
- routine `dev/uat/prod` roots own stable account/domain infrastructure.
- `workspace-access` owns stable DEV personal/CI workspace permissions, not individual PR schemas.
- human domain RBAC attaches only to stable environment databases; `CI_<DOMAIN>` uses `AR_<DOMAIN>_CI`.
- employee membership comes from IdP/SCIM, not Terraform user records.
- backend profile is selected at runtime (`azurerm` or `s3`).
- Terraform state, real tfvars, keys/passwords/tokens are never committed.

## 3. `enterprise-snowflake-data-project-framework`

Current implemented first slice plus target growth:

```text
enterprise-snowflake-data-project-framework/
├── README.md
├── pyproject.toml
├── src/enterprise_snowflake_framework/
│   ├── __init__.py
│   ├── workspaces.py                         # implemented
│   └── query_tags.py                         # implemented
├── scripts/
│   ├── render_workspace_sql.py               # implemented
│   └── render_query_tag.py                   # implemented
├── tests/
│   ├── test_workspaces.py                    # implemented
│   └── test_query_tags.py                    # implemented
├── docs/patterns/
│   └── workspaces-and-query-tags.md          # implemented
├── .github/workflows/
│   └── framework-ci.yml                      # implemented
│
├── dbt_package/                              # Phase 2
│   ├── dbt_project.yml
│   ├── macros/
│   │   ├── environment/
│   │   ├── loading/{full_refresh,append_only,incremental_merge}/
│   │   ├── scd2/{snapshot,merge,stream_task}/
│   │   ├── reconciliation/
│   │   ├── freshness/
│   │   ├── audit/
│   │   └── operations/
│   └── tests/generic/
├── project_schema/                           # Phase 2
│   ├── project.schema.json
│   ├── dataset.schema.json
│   └── raw_contract.schema.json
└── .github/workflows/                        # additional reusable workflows later
    ├── pr-ci.yml
    ├── deploy-dev.yml
    ├── promote-uat.yml
    ├── promote-prod.yml
    ├── rollback-prod.yml
    ├── recover-data.yml
    └── backfill.yml
```

Rules:

- framework code owns generic technical behaviour, never domain business SQL;
- project repos consume pinned framework versions;
- metadata validation must not become a second orchestration language;
- workspace/query-tag utilities are deliberately dependency-light and reusable by GitHub workflows/dbt tooling.

## 4. `enterprise-snowflake-demo-source-systems`

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

## 5. `enterprise-snowflake-health-analytics`

Target:

```text
enterprise-snowflake-health-analytics/
├── README.md
├── config/
│   ├── project.yml
│   ├── datasets/
│   ├── contracts/raw/
│   └── operations/
├── dbt/
│   ├── dbt_project.yml
│   ├── packages.yml
│   ├── models/{staging,intermediate,canonical,marts,semantic}/
│   ├── snapshots/
│   ├── tests/{singular,domain}/
│   └── seeds/
├── ingestion/openflow/                      # Phase 8 only
└── .github/workflows/
    ├── pr-ci.yml
    ├── deploy-dev.yml
    ├── promote-uat.yml
    └── promote-prod.yml
```

Health owns domain SQL/contracts/tests; generic mechanics remain in the framework.

## 6. `enterprise-snowflake-transport-analytics`

Target:

```text
enterprise-snowflake-transport-analytics/
├── README.md
├── config/
│   ├── project.yml
│   ├── datasets/
│   ├── contracts/raw/
│   └── operations/
├── dbt/
│   ├── dbt_project.yml
│   ├── packages.yml
│   ├── models/{staging,intermediate,canonical,marts,semantic}/
│   ├── snapshots/
│   ├── tests/{singular,domain}/
│   └── seeds/
├── ingestion/
│   ├── snowpipe_streaming/
│   └── kafka_connector/
└── .github/workflows/
    ├── pr-ci.yml
    ├── deploy-dev.yml
    ├── promote-uat.yml
    └── promote-prod.yml
```

Direct Snowpipe Streaming and Kafka Connector later target the same logical RAW event contract; normally one path is active.

## 7. Dependency direction

```text
platform-infra
    │ provisions accounts/RBAC/warehouses/guardrails
    ▼
health-analytics / transport-analytics
    ▲
    │ consume pinned framework releases
    │
data-project-framework

source-systems
    │ external-style data/events
    ▼
RAW contract -> project downstream
```

Rules:

- framework never imports project business code;
- platform infra never owns Health/Transport business models;
- source simulator never depends on downstream analytics;
- project repos do not call each other directly.

## 8. Deferred paths

Do not create cosmetic placeholders for:

```text
Kafka Connector
Snowpipe Streaming
Openflow
full governance policies
full observability dashboards
production rollback automation
```

Current next growth belongs in project-CI identity/workflow, metadata schemas/validation and dbt environment-resolution primitives.
