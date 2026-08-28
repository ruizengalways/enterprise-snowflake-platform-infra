# Canonical Repository Directory Layout

> **Status:** Accepted architecture plan
>
> **Scope:** All five Enterprise Snowflake repositories
>
> **Rule:** Git does not track empty directories. Create a directory only with its first real file; do not add `.gitkeep` theatre.

## 1. Design principles

1. Repository boundaries come before folder convenience.
2. One concern has one authoritative location.
3. Health/Transport repositories stay thin; shared technical behaviour belongs in the framework/platform.
4. Reusable GitHub workflows live under `.github/workflows/`.
5. Terraform is split into reusable capability modules plus one root stack per Snowflake account.
6. Snowflake-native SQL is separated by lifecycle purpose from dbt models.
7. Configuration is non-secret metadata, never credentials.
8. Planned folders are not created until implementation reaches them.

## 2. `enterprise-snowflake-platform-infra`

```text
enterprise-snowflake-platform-infra/
├── README.md
├── .gitignore
├── .editorconfig
├── .terraform-version
│
├── docs/
│   ├── PROJECT_BLUEPRINT.md
│   ├── architecture/
│   │   ├── REPOSITORY_LAYOUT.md
│   │   ├── ACCOUNT_TOPOLOGY.md
│   │   ├── RBAC_MODEL.md
│   │   └── RELEASE_AND_RECOVERY.md          # Phase 3
│   ├── adr/
│   │   └── ADR-*.md
│   ├── standards/
│   │   ├── NAMING_CONVENTIONS.md
│   │   ├── TERRAFORM_STANDARDS.md
│   │   └── SQL_STANDARDS.md                 # when native SQL begins
│   └── runbooks/
│       └── ...                               # deployment/recovery/incidents later
│
├── config/
│   ├── environments/
│   │   ├── dev.yml
│   │   ├── uat.yml
│   │   └── prod.yml
│   ├── projects/
│   │   └── ...                               # when generic project onboarding begins
│   ├── access-profiles/
│   │   └── ...
│   └── governance/
│       └── ...
│
├── terraform/
│   ├── README.md
│   ├── modules/
│   │   ├── analytics-environment/           # project database + stable schemas
│   │   ├── warehouse/                       # standard warehouse guardrails
│   │   ├── rbac/                            # account/database roles + grants
│   │   ├── platform-control/                # PLATFORM_CONTROL structure
│   │   ├── workload-identity/               # later Phase 1
│   │   └── cost-controls/                   # later Phase 1
│   └── stacks/
│       ├── dev/
│       │   ├── versions.tf
│       │   ├── providers.tf
│       │   ├── main.tf
│       │   └── outputs.tf
│       ├── uat/
│       │   ├── versions.tf
│       │   ├── providers.tf
│       │   ├── main.tf
│       │   └── outputs.tf
│       └── prod/
│           ├── versions.tf
│           ├── providers.tf
│           ├── main.tf
│           └── outputs.tf
│
├── snowflake/
│   ├── bootstrap/                           # only if privileged SQL bootstrap is required
│   ├── control/{ddl,procedures,tasks}/
│   ├── governance/{tags,masking,row-access}/
│   ├── monitoring/{views,queries}/
│   ├── alerts/
│   └── recovery/{clone-swap,validation}/
│
└── .github/
    └── workflows/
        ├── terraform-ci.yml
        ├── terraform-plan-dev.yml            # after state/WIF
        ├── terraform-apply-dev.yml           # protected
        ├── terraform-plan-uat.yml            # later
        ├── terraform-apply-uat.yml            # protected
        ├── terraform-plan-prod.yml           # later
        └── terraform-apply-prod.yml           # protected/approved
```

### Platform Infra rules

- Organization-level creation of DEV/UAT/PROD is a separate privileged bootstrap lifecycle; normal account stacks assume the target account exists.
- `terraform/` owns selected stable infrastructure state.
- `snowflake/` owns selected native SQL objects when Terraform/dbt is not the clearer lifecycle owner.
- `config/` provides non-secret declarative inputs.
- Terraform state, real `.tfvars`, keys, passwords and tokens are never committed.
- No separate top-level `observability/` folder unless a future asset type genuinely needs it; native monitoring SQL begins under `snowflake/monitoring/`.

## 3. `enterprise-snowflake-data-project-framework`

```text
enterprise-snowflake-data-project-framework/
├── README.md
├── CHANGELOG.md
├── dbt_package/
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
├── project_schema/
│   ├── project.schema.json
│   ├── dataset.schema.json
│   └── raw_contract.schema.json
├── validation/
├── bootstrap/{templates,scripts}/
├── examples/{minimal-project,metadata}/
├── docs/{patterns,operations}/
└── .github/workflows/
    ├── framework-ci.yml
    ├── pr-ci.yml
    ├── deploy-dev.yml
    ├── promote-uat.yml
    ├── promote-prod.yml
    ├── rollback-prod.yml
    ├── recover-data.yml
    └── backfill.yml
```

Framework rules: versioned dependency, no domain SQL, reusable workflows are callable via pinned tag/SHA, metadata validation stays technical rather than becoming a second orchestration language.

## 4. `enterprise-snowflake-demo-source-systems`

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

This repository represents the external world and stops at the source/RAW boundary. It contains no downstream marts/semantic/SCD2 business logic.

## 5. `enterprise-snowflake-health-analytics`

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
└── .github/workflows/{pr-ci,deploy-dev,promote-uat,promote-prod}.yml
```

Health owns source-specific RAW contracts/config and genuine Health SQL. Generic SCD2/reconciliation/freshness/recovery primitives remain framework capabilities.

## 6. `enterprise-snowflake-transport-analytics`

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
├── ingestion/{snowpipe_streaming,kafka_connector}/
└── .github/workflows/{pr-ci,deploy-dev,promote-uat,promote-prod}.yml
```

Direct Snowpipe Streaming and Kafka Connector paths target the same logical RAW event contract; normally only one is active for a given run/environment.

## 7. Dependency direction

```text
platform-infra ──provisions guardrails──> health / transport
framework ──pinned package/workflows────> health / transport
demo-source-systems ──external data─────> RAW contract ──> projects
```

Framework never imports project code; Platform Infra contains no Health/Transport business models; project repositories do not call one another.

## 8. Intentionally deferred paths

Do not create cosmetic placeholder implementations for Kafka, Snowpipe Streaming, Openflow, masking/RAP, rollback automation, recovery procedures, semantic regression, full reconciliation/observability, or account apply workflows before their phase starts.

## 9. Current Phase 1 structure

Real Phase 1 paths now include:

```text
config/environments/{dev,uat,prod}.yml
terraform/modules/{analytics-environment,warehouse,rbac,platform-control}/
terraform/stacks/{dev,uat,prod}/
.github/workflows/terraform-ci.yml
docs/architecture/{ACCOUNT_TOPOLOGY,RBAC_MODEL,REPOSITORY_LAYOUT}.md
```

Next directory growth should be driven by remote state + workload identity + cost-control implementation, not placeholder architecture.
