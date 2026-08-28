# Canonical Repository Directory Layout

> **Status:** Accepted architecture plan
>
> **Scope:** All five Enterprise Snowflake repositories
>
> **Rule:** Git does not track empty directories. Create a directory only with its first real file; do not add `.gitkeep` theatre.

## 1. Design principles

1. Repository boundaries come before folder convenience.
2. One concern has one authoritative location.
3. Health/Transport repositories stay thin; shared technical behaviour belongs in framework/platform repositories.
4. Reusable GitHub workflows live under `.github/workflows/`.
5. Terraform is split into reusable capability modules plus isolated deployable roots.
6. Organization-level Terraform is separate from routine account-level Terraform.
7. Snowflake-native SQL is separated by lifecycle purpose from dbt models.
8. Configuration is non-secret metadata, never credentials.
9. Planned folders appear only when implementation reaches them.

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
│   ├── organization.yml                     # DEV/UAT/PROD account contract
│   ├── environments/
│   │   ├── dev.yml
│   │   ├── uat.yml
│   │   └── prod.yml
│   ├── projects/
│   │   └── ...                               # generic domain onboarding later
│   ├── access-profiles/
│   │   └── ...
│   └── governance/
│       └── ...
│
├── terraform/
│   ├── README.md
│   ├── modules/
│   │   ├── analytics-environment/           # one domain database + stable schemas
│   │   ├── warehouse/                       # standard warehouse guardrails
│   │   ├── rbac/                            # platform/domain roles + database roles + grants
│   │   ├── platform-control/                # PLATFORM_CONTROL structure
│   │   ├── workload-identity/               # later Phase 1
│   │   └── cost-controls/                   # later Phase 1
│   └── stacks/
│       ├── organization/                    # ORGADMIN only; account creation/import
│       │   ├── versions.tf
│       │   ├── providers.tf
│       │   ├── variables.tf
│       │   ├── main.tf
│       │   └── outputs.tf
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

- `organization/` is the only root allowed to use ORGADMIN; normal account stacks never create Snowflake accounts.
- Organization/DEV/UAT/PROD eventually use independent remote state.
- `terraform/` owns selected stable infrastructure state.
- `snowflake/` owns selected native SQL objects when Terraform/dbt is not the clearer lifecycle owner.
- `config/` provides non-secret declarative inputs.
- Terraform state, real `.tfvars`, private keys, passwords and tokens are never committed.
- No separate top-level `observability/` folder unless a future asset type genuinely requires it.

### Current Phase 1 domain convention

Each domain receives environment databases and workload compute rather than one database per physical source:

```text
DEV_HEALTH / UAT_HEALTH / PROD_HEALTH
DEV_TRANSPORT / UAT_TRANSPORT / PROD_TRANSPORT

WH_HEALTH_QUERY / WH_HEALTH_TRANSFORM
WH_TRANSPORT_QUERY / WH_TRANSPORT_TRANSFORM
```

DEV additionally contains `CI_<DOMAIN>` databases and `WH_<DOMAIN>_CI` warehouses.

RBAC is domain-specific and includes `GUEST -> READER -> DEVELOPER -> ADMIN`; GUEST is published-data read-only.

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

Rules:

- reusable workflows are versioned dependencies called from project repos;
- framework code owns generic technical behaviour, never domain business SQL;
- metadata validation must not become a second orchestration framework.

## 4. `enterprise-snowflake-demo-source-systems`

```text
enterprise-snowflake-demo-source-systems/
├── README.md
├── pyproject.toml
├── .env.example
├── sources/{health,transport}/
├── adapters/{rest,sse,gtfs_realtime}/
├── sinks/{files,sql_server,snowflake_direct,snowpipe_streaming,kafka}/
├── scenarios/{normal,late_arriving,out_of_order,duplicates,deletes,bad_data,source_outage,schema_change,volume_spike}/
├── config/{health,transport}/
└── tests/{unit,integration}/
```

Rules:

- represents the world outside Snowflake;
- source generators are independent of delivery technology;
- stops at the source/RAW boundary;
- no dbt, marts, semantic, downstream reconciliation or project SCD2 logic.

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
└── .github/workflows/
    ├── pr-ci.yml
    ├── deploy-dev.yml
    ├── promote-uat.yml
    └── promote-prod.yml
```

Health owns traditional batch/CDC/PII/SCD2/late-arrival/reconciliation/recovery domain behaviour. Generic mechanics remain in the framework.

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
├── ingestion/
│   ├── snowpipe_streaming/
│   └── kafka_connector/
└── .github/workflows/
    ├── pr-ci.yml
    ├── deploy-dev.yml
    ├── promote-uat.yml
    └── promote-prod.yml
```

Direct Snowpipe Streaming and Kafka Connector paths target the same project-owned RAW event contract; normally one path is active.

## 7. Dependency direction

```text
platform-infra
    │ provisions guardrails/infrastructure
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

- framework never imports project code;
- platform infra never owns Health/Transport business models;
- source simulator never depends on downstream analytics;
- projects consume pinned framework releases and do not call each other directly.

## 8. Intentionally deferred paths

Do not create cosmetic placeholder content before the relevant phase for:

- Kafka Connector;
- direct Snowpipe Streaming;
- Openflow;
- masking/row-access policies;
- workload identity implementation;
- cost-control implementation;
- production rollback automation;
- recovery procedures;
- semantic regression tooling;
- full reconciliation engine;
- full observability dashboards.

The repository tree grows with working capabilities, not ahead of them.
