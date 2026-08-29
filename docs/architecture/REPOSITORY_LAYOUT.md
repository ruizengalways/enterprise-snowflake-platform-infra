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
6. Organization bootstrap, workload-identity bootstrap and routine account infrastructure use separate lifecycle/state roots.
7. Terraform state backend selection is an execution adapter, not domain/platform business logic.
8. Snowflake-native SQL is separated by lifecycle purpose from dbt models.
9. Configuration is non-secret metadata, never credentials.
10. Planned folders appear only when implementation reaches them.

## 2. `enterprise-snowflake-platform-infra`

```text
enterprise-snowflake-platform-infra/
├── README.md
├── .gitignore
├── .editorconfig
├── .terraform-version
│
├── docs/
│   ├── CURRENT_CONTEXT.md                  # first read in a new conversation
│   ├── PROJECT_BLUEPRINT.md                # long-term canonical architecture
│   ├── architecture/
│   │   ├── REPOSITORY_LAYOUT.md
│   │   ├── ACCOUNT_TOPOLOGY.md
│   │   ├── RBAC_MODEL.md
│   │   ├── TERRAFORM_STATE_AND_IDENTITY.md
│   │   └── RELEASE_AND_RECOVERY.md         # Phase 3
│   ├── adr/
│   │   └── ADR-*.md
│   ├── standards/
│   │   ├── NAMING_CONVENTIONS.md
│   │   ├── TERRAFORM_STANDARDS.md
│   │   └── SQL_STANDARDS.md                # when native SQL begins
│   └── runbooks/
│       └── terraform-platform-bootstrap.md
│
├── config/
│   ├── organization.yml                    # DEV/UAT/PROD account contract
│   ├── environments/
│   │   ├── dev.yml                         # includes Terraform WIF metadata
│   │   ├── uat.yml
│   │   └── prod.yml
│   ├── projects/                           # generic domain onboarding later
│   ├── access-profiles/
│   └── governance/
│
├── terraform/
│   ├── README.md
│   ├── backend-profiles/
│   │   ├── azurerm/backend.tf              # Azure Blob partial backend declaration
│   │   └── s3/backend.tf                   # S3 partial backend + native lockfile
│   ├── scripts/
│   │   └── select-backend.sh               # materialises ignored backend.generated.tf
│   ├── modules/
│   │   ├── analytics-environment/          # one domain database + stable schemas
│   │   ├── warehouse/                      # standard warehouse guardrails
│   │   ├── rbac/                           # platform/domain roles + DB roles + grants
│   │   ├── platform-control/               # PLATFORM_CONTROL structure
│   │   ├── workload-identity/              # GitHub OIDC SERVICE user + AR_TERRAFORM role
│   │   └── cost-controls/                  # later Phase 1
│   └── stacks/
│       ├── organization/                   # ORGADMIN only; account creation/import
│       ├── identity/
│       │   ├── dev/                        # ACCOUNTADMIN bootstrap only
│       │   ├── uat/
│       │   └── prod/
│       ├── dev/                            # routine AR_TERRAFORM_DEV
│       ├── uat/                            # routine AR_TERRAFORM_UAT
│       └── prod/                           # routine AR_TERRAFORM_PROD
│
├── snowflake/
│   ├── bootstrap/                          # only if privileged SQL bootstrap is required
│   ├── control/{ddl,procedures,tasks}/
│   ├── governance/{tags,masking,row-access}/
│   ├── monitoring/{views,queries}/
│   ├── alerts/
│   └── recovery/{clone-swap,validation}/
│
└── .github/
    └── workflows/
        ├── terraform-ci.yml                # fmt + 7 roots + both backend profiles
        ├── terraform-plan-dev.yml          # implemented; Azure Blob or S3 + Snowflake WIF
        ├── terraform-apply-dev.yml          # only after real DEV plan review
        ├── terraform-plan-uat.yml           # after DEV is proven
        ├── terraform-apply-uat.yml
        ├── terraform-plan-prod.yml          # after UAT is proven
        └── terraform-apply-prod.yml         # protected/approved
```

### Platform Infra rules

- `organization/` is the only root allowed to use ORGADMIN; routine account stacks never create Snowflake accounts.
- `identity/<env>/` owns the platform Terraform service user, OIDC trust and `AR_TERRAFORM_<ENV>` role; routine state never owns its own authentication identity.
- Routine `dev/uat/prod` roots activate only their dedicated Terraform machine role.
- Terraform roots do **not** commit a cloud-specific backend block. The runtime selector materialises either Azure Blob (`azurerm`) or S3.
- `backend.generated.tf` is ignored and is never canonical source.
- One deployment has one authoritative writable remote-state backend. Do not mirror a live state as writable in both Azure Blob and S3.
- OneDrive/SharePoint may store docs/evidence but not authoritative live Terraform state.
- `terraform/` owns selected stable infrastructure state.
- `snowflake/` owns selected native SQL objects when Terraform/dbt is not the clearer lifecycle owner.
- `config/` provides non-secret declarative inputs. OIDC subjects may be committed; credentials/tokens may not.
- Terraform state, real `.tfvars`, private keys, passwords, cloud access keys and tokens are never committed.

### Current Phase 1 domain convention

```text
DEV_HEALTH / CI_HEALTH / UAT_HEALTH / PROD_HEALTH
DEV_TRANSPORT / CI_TRANSPORT / UAT_TRANSPORT / PROD_TRANSPORT

WH_HEALTH_QUERY / WH_HEALTH_TRANSFORM / WH_HEALTH_CI
WH_TRANSPORT_QUERY / WH_TRANSPORT_TRANSFORM / WH_TRANSPORT_CI
```

RBAC is domain-specific and includes `GUEST -> READER -> DEVELOPER -> ADMIN`; GUEST is published-data read-only.

Employee role membership belongs to enterprise identity/SCIM, not Terraform user-by-user grants.

### Current state/identity convention

Microsoft-first state path:

```text
GitHub OIDC -> Microsoft Entra federation -> Azure Blob state
GitHub OIDC -> SU_GITHUB_TERRAFORM_<ENV> -> AR_TERRAFORM_<ENV> -> Snowflake Terraform
```

AWS alternative:

```text
GitHub OIDC -> AWS IAM -> S3 state/.tflock
GitHub OIDC -> SU_GITHUB_TERRAFORM_<ENV> -> AR_TERRAFORM_<ENV> -> Snowflake Terraform
```

The first remote execution path is manual DEV plan only. UAT/PROD plan/apply workflows stay deferred until the previous environment is proven.

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

Shared framework code owns generic technical behaviour, never domain business SQL.

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

This repository represents the world outside Snowflake and stops at the source/RAW boundary.

## 5. `enterprise-snowflake-health-analytics`

```text
enterprise-snowflake-health-analytics/
├── README.md
├── config/{project.yml,datasets,contracts/raw,operations}
├── dbt/
│   ├── dbt_project.yml
│   ├── packages.yml
│   ├── models/{staging,intermediate,canonical,marts,semantic}/
│   ├── snapshots/
│   ├── tests/{singular,domain}/
│   └── seeds/
├── ingestion/openflow/                     # Phase 8 only
└── .github/workflows/{pr-ci,deploy-dev,promote-uat,promote-prod}.yml
```

Health owns domain-specific batch/CDC/PII/SCD2/late-arrival/reconciliation/recovery behaviour. Generic mechanics remain in the framework.

## 6. `enterprise-snowflake-transport-analytics`

```text
enterprise-snowflake-transport-analytics/
├── README.md
├── config/{project.yml,datasets,contracts/raw,operations}
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

Framework never imports project code; platform infra never owns domain business models; source simulation never depends on downstream analytics.

## 8. Intentionally deferred paths

Do not create cosmetic placeholder content before the relevant phase for:

- Kafka Connector;
- direct Snowpipe Streaming;
- Openflow;
- masking/row-access policies;
- cost-control implementation;
- DEV apply automation until real DEV plan is reviewed;
- UAT/PROD platform plan/apply automation until the preceding environment is proven;
- project CI/deployment workload identities;
- production rollback automation;
- recovery procedures;
- semantic regression tooling;
- full reconciliation engine;
- full observability dashboards.

The repository tree grows with working capabilities, not ahead of them.
