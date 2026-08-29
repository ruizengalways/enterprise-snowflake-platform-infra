# Enterprise Snowflake Platform — Project Blueprint

> **Status:** Phase 1 in progress — platform/domain/workspace/project-CI/metadata foundations implemented in source/static CI; live remote state + Snowflake apply/verification remain.
>
> **Authority:** Canonical long-term architecture.
>
> **Fast handoff:** Read [`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) first in a new conversation/session.

## 1. Goal

Build a production-grade reusable Snowflake platform/reference implementation suitable for real enterprise adoption and senior/principal data/platform engineering.

Core outcomes:

- clear ownership and lifecycle boundaries;
- repeatable domain/source onboarding;
- stable RAW contracts independent of ingestion technology;
- metadata-driven common technical behaviour without hiding business logic;
- immutable Git SHA promotion;
- DEV/UAT/PROD account isolation;
- least-privilege human and machine identity;
- recoverability/reconciliation/freshness/observability/cost attribution;
- multiple approved implementations where workloads genuinely differ.

## 2. Non-goals

- do not merge Metric Guard into this project;
- do not maximise technology count for appearance;
- do not Terraform-manage every Snowflake object;
- do not turn YAML into a programming language;
- do not use DEV/UAT/PROD Git branches;
- do not use Dynamic Tables for SCD2;
- do not introduce Spark Streaming without a concrete requirement;
- Marketplace Secure Shares do not replace ingestion;
- do not build a custom ITSM system.

## 3. Principles

1. Convention over copy/paste.
2. Configuration for stable technical behaviour; explicit SQL/code for genuine business differences.
3. Domain autonomy inside platform guardrails.
4. RAW contracts isolate ingestion technology from downstream engineering.
5. Promote the same immutable Git SHA through environments.
6. Human identity and machine identity are separate.
7. Production readiness includes recovery/reconciliation, not deployment success alone.
8. One Snowflake object has one authoritative lifecycle owner.
9. Git is configuration truth; `PLATFORM_CONTROL` stores runtime/operational state.
10. Prefer deterministic replay/rebuild over manual PROD DML.
11. Account, database, schema and warehouse boundaries solve different problems.
12. Cost attribution is multi-dimensional; do not create database-per-source for chargeback.
13. Consumer access is narrower than engineering access.
14. Bootstrap identity/state is separated from automation that consumes it.
15. Avoid long-lived CI credentials when federation is available.
16. Personal DEV schema names are namespaces, not fake security boundaries.

## 4. Repository model

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

| Repository | Responsibility |
|---|---|
| platform-infra | Snowflake accounts/platform Terraform, RBAC, warehouses, WIF/state, workspace/cost/governance/control foundation |
| data-project-framework | reusable metadata/workspace/query-tag/dbt/load/SCD2/DQ/reconciliation/delivery mechanics |
| demo-source-systems | deterministic external-style source/event simulation only |
| health-analytics | Health contracts/config/business SQL/tests/semantic/ingestion config |
| transport-analytics | Transport contracts/config/business SQL/tests/semantic/streaming config |

Projects stay thin and pin framework code/workflows deliberately.

## 5. Account topology

```text
Snowflake Organization
├── DEV
│   ├── DEV_HEALTH
│   ├── CI_HEALTH
│   ├── DEV_TRANSPORT
│   ├── CI_TRANSPORT
│   └── PLATFORM_CONTROL
├── UAT
│   ├── UAT_HEALTH
│   ├── UAT_TRANSPORT
│   └── PLATFORM_CONTROL
└── PROD
    ├── PROD_HEALTH
    ├── PROD_TRANSPORT
    └── PLATFORM_CONTROL
```

CI is not a fourth account. UAT is a real account so account-scoped identities/integrations/RBAC/parameters can be proven before PROD.

See ADR-018.

## 6. Database/schema boundary

```text
<ENVIRONMENT>_<DOMAIN>
```

A database represents environment × governed data product/domain, not a physical source.

Stable schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Published consumer schemas initially: `MARTS`, `SEMANTIC`.

RAW source-purpose schemas are onboarding-driven, e.g. `RAW_EHR_MSSQL`, not pre-created speculatively.

See ADR-019.

## 7. Human RBAC and identity governance

Per domain:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

Stable domain database roles:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
  -> DR_<DOMAIN>_ANALYTICS_READ
  -> DR_<DOMAIN>_ANALYTICS_WRITE
  -> DR_<DOMAIN>_ANALYTICS_OWNER
```

Policy:

- GUEST = authenticated MARTS/SEMANTIC read-only;
- READER = all stable-layer read;
- DEV DEVELOPER = WRITE;
- UAT/PROD DEVELOPER = read-only by default;
- domain authority never crosses into another domain unless explicitly granted.

Terraform defines the role/privilege model. Enterprise IdP/SCIM controls membership:

```text
Employee/contractor
 -> Entra ID / Okta group
 -> SCIM / approved provisioning
 -> AR_<DOMAIN>_<CAPABILITY>
```

Adding/removing an employee from an existing domain does not require Terraform.

See ADR-020.

## 8. Compute boundary

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
WH_PLATFORM_OPS
```

Account identifies environment; warehouse identifies domain + workload.

Environment project metadata carries query/transform/CI warehouse keys; root Terraform derives grants rather than hard-coding Health/Transport blocks.

Baseline remains conservative: XSMALL, auto-resume, ~60s auto-suspend, initially suspended, explicit statement timeout, no multi-cluster/query acceleration without evidence.

## 9. DEV personal workspaces

Human DEV roles attach only to `DEV_<DOMAIN>` databases.

DEV WRITE receives `CREATE SCHEMA` on the matching DEV database.

```text
<DEVELOPER>_<LAYER>
```

Example: `DEV_HEALTH.ALICE_SMITH_STAGING`.

This is a namespace/workspace convention, not per-person isolation. Stronger isolation requires identity-governed personal roles.

## 10. PR CI workspaces

Human GUEST/READER/DEVELOPER/ADMIN roles do not attach to `CI_<DOMAIN>`.

Machine capability:

```text
AR_<DOMAIN>_CI
 -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
    -> USAGE + CREATE SCHEMA on CI_<DOMAIN>
 -> USAGE on WH_<DOMAIN>_CI
```

PR schemas:

```text
PR_<NUMBER>_<LAYER>
```

Framework rendering creates transient schemas with zero-day Time Travel and prefix-guarded cleanup.

See ADR-025.

## 11. Terraform roots and lifecycle ordering

Current roots:

```text
terraform/stacks/organization/
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
terraform/stacks/dev/
terraform/stacks/project-identity/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

There are eight independent state boundaries.

Lifecycle intent:

```text
organization
 -> identity/dev
 -> platform/dev
 -> project-identity/dev
 -> UAT
 -> PROD
```

`organization/` alone uses ORGADMIN.

`identity/<env>` may use ACCOUNTADMIN only to bootstrap platform Terraform WIF.

Routine `dev/uat/prod` use only `AR_TERRAFORM_<ENV>`.

`project-identity/dev` runs after platform/dev because it binds project service users to existing CI roles created by platform state.

Terraform/provider baseline:

```text
Terraform 1.16.0
snowflakedb/snowflake 2.19.0
```

Current modules:

```text
analytics-environment
warehouse
platform-control
rbac
workspace-access
workload-identity
service-identity
```

## 12. Platform Terraform WIF

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Routine account privileges initially:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

No routine ACCOUNTADMIN/SYSADMIN/SECURITYADMIN.

OIDC subjects are repo + GitHub Environment scoped. Snowflake OIDC audience is account-scoped; shared `snowflakecomputing.com` is rejected.

See ADR-023.

## 13. Project PR-CI WIF

Source implementation now derives:

```text
SU_GITHUB_HEALTH_CI
 -> AR_HEALTH_CI
 -> repo:ruizengalways/enterprise-snowflake-health-analytics:environment:ci

SU_GITHUB_TRANSPORT_CI
 -> AR_TRANSPORT_CI
 -> repo:ruizengalways/enterprise-snowflake-transport-analytics:environment:ci
```

Generic `service-identity` creates SERVICE user/WIF and assigns an existing role only; no account-level privileges.

Separate state:

```text
enterprise-snowflake-platform-infra/project-identity/dev/terraform.tfstate
```

See ADR-027.

## 14. Remote Terraform state

Snowflake is not AWS-dependent.

```text
azurerm -> Azure Blob (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

Backend type is materialised at execution time through:

```text
terraform/backend-profiles/{azurerm,s3}/backend.tf
terraform/scripts/select-backend.sh
```

OneDrive/SharePoint is for human-facing docs/evidence, not live Terraform state.

One deployment has one writable state backend; Azure/S3 are not dual writers.

See ADR-024.

## 15. Framework metadata contracts

Version 1 framework JSON Schemas now exist for:

```text
project metadata
  code, name, repository, owner_team

dataset metadata
  id, owner_team, raw_contract
  load_strategy, implementation
  business_key, watermark_column
  freshness, reconciliation

RAW contract
  source_system, entity, grain, business_key
  source_timestamp
  columns/types/nullability/classification
  snapshot|append|cdc semantics
  cadence, retention_days, breaking_change_policy
```

Validator performs structural + bounded technical semantic checks such as contract references, duplicate IDs/columns, keyed-strategy keys, freshness threshold ordering and CDC operation/sequence columns.

Metadata does **not** encode business joins, formulas, arbitrary SQL or workflow branching.

Escape hatch:

```yaml
implementation: custom
```

Custom implementations still participate in tests/reconciliation/observability/recovery.

See ADR-028.

## 16. Query-tag contract and cost attribution

Framework query tags use compact JSON.

Required:

```text
project
environment
workload
```

Optional:

```text
source
pipeline
dataset
run_id
git_sha
pr_number
operation
```

Do not include personal/secret/regulated/business payload data.

Cost model:

```text
Domain storage/recovery         -> <ENVIRONMENT>_<DOMAIN>
Compute                         -> WH_<DOMAIN>_<WORKLOAD>
Query execution                 -> QUERY_TAG + QUERY_ATTRIBUTION_HISTORY
Warehouse idle                  -> WAREHOUSE_METERING_HISTORY
Serverless/ingestion            -> service-specific usage histories
Storage detail                  -> Snowflake storage histories/metrics
```

Query-attributed compute excludes warehouse idle time; it is not the complete warehouse bill.

Baseline SQL: `snowflake/monitoring/queries/cost_attribution.sql`.

See ADR-026.

## 17. Reusable PR workspace workflow

Framework:

```text
enterprise-snowflake-data-project-framework/.github/workflows/pr-workspace.yml
```

Thin callers:

```text
health-analytics/.github/workflows/pr-workspace.yml
transport-analytics/.github/workflows/pr-workspace.yml
```

Callers pin framework commit `7ffafbc83ec7da154f036613541bf34b8a913e1a`.

Lifecycle:

```text
PR opened/reopened/synchronize -> create idempotent PR_<n>_* schemas
PR closed                      -> drop only PR_<n>_* schemas
```

The workflow:

- targets GitHub Environment `ci`;
- installs the pinned framework;
- renders QUERY_TAG + guarded workspace SQL;
- installs Snowflake CLI 3.25.0 via Snowflake Actions pinned to commit `1160898243c351349621a6c2bac2e455ab1077b2` (v3.3.1);
- explicitly requests a GitHub OIDC token with the configured account-scoped audience;
- authenticates as `SU_GITHUB_<DOMAIN>_CI` / `AR_<DOMAIN>_CI`;
- executes only generated local SQL with `snow sql --local-only --enhanced-exit-codes`.

It currently does **not** execute arbitrary/untrusted PR project code under Snowflake credentials.

No live project-CI identity/environment exists yet, so this workflow has not created a real Snowflake schema.

## 18. RAW contract boundary

Project-owned RAW contracts define source/entity/schema version/grain/business key/required columns/types/nullability/source timestamp/CDC semantics/sequence/cadence/retention/classification/breaking-change policy.

Typical technical fields:

```text
source_operation
source_sequence
source_updated_at
ingested_at
batch_id
source_system
```

All ingestion paths must converge on the RAW contract so downstream design is technology-independent.

## 19. Transformation / load strategy catalog

```text
RAW -> staging -> intermediate/canonical -> marts -> semantic
```

Approved strategies:

```text
full_refresh
append_only
incremental_merge
scd2_snapshot
scd2_merge
scd2_stream_task
```

Dynamic Tables are not an approved SCD2 implementation.

SCD2 testing must cover unchanged/changed rows, composite keys, duplicates, multiple changes, late/out-of-order events, deletes, idempotency, backfill and deterministic rebuild.

## 20. CI/CD target

Project delivery:

```text
feature branch
-> personal/shared DEV
-> PR CI in CI_<DOMAIN>
-> merge
-> UAT
-> approval
-> PROD
-> smoke + DQ + reconciliation
```

Promote the same immutable Git SHA. PR close cleans PR workspaces.

Platform infrastructure:

```text
static CI
-> organization bootstrap/import
-> identity/dev
-> platform/dev remote plan/apply/verify
-> project-identity/dev
-> live PR workspace test
-> UAT
-> protected PROD
```

## 21. Recovery / rollback

Derived PROD analytics rollback target:

```text
pre-release zero-copy clone
-> deploy
-> smoke/DQ/reconciliation
-> PASS retain
-> FAIL controlled SWAP to known-good state
-> validate/reconcile/resume
```

Do not blindly roll back RAW. Prefer replay/checkpoint/backfill/Time Travel/UNDROP/clone/rebuild over manual PROD DML.

## 22. Data quality / reconciliation / freshness

DQ baseline: not-null, uniqueness, relationships, accepted values, domain assertions, volume, SCD2 invariants, schema contracts.

Reconciliation: row count, distinct business keys, control totals, min/max business timestamp, watermarks, rejected rows, duplicates.

Freshness is tracked separately as source freshness, pipeline/processed watermark and published dataset freshness.

Dataset readiness can require transform + DQ + reconciliation + freshness + semantic regression.

## 23. Semantic layer

Use Snowflake-native Semantic Views. Cube is excluded.

## 24. New-domain onboarding target

For `FINANCE` the platform should derive:

```text
DEV_FINANCE / CI_FINANCE / UAT_FINANCE / PROD_FINANCE

AR_FINANCE_GUEST / READER / DEVELOPER / ADMIN / CI
DR_FINANCE_ANALYTICS_GUEST / READ / WRITE / OWNER
CI_FINANCE.DR_FINANCE_CI_WORKSPACE

WH_FINANCE_QUERY / TRANSFORM / CI
SU_GITHUB_FINANCE_CI
```

Adding the domain should primarily mean metadata/config + a project repo, not cloned Terraform branches. Employee growth does not add Terraform user records.

## 25. Roadmap

- **Phase 0 — Architecture:** complete.
- **Phase 1 — Platform Foundation:** in progress; static accounts/RBAC/state/WIF/workspaces/project-CI identity/metadata/query-tag/cost baseline implemented; live remote state/apply verification remains.
- **Phase 2 — Framework Foundation:** dbt environment resolution, metadata-driven basic loads, DQ/reconciliation/freshness/audit primitives.
- **Phase 3 — Thin CI/CD spine:** prove DEV -> PR CI -> UAT -> PROD with exact SHA and cleanup/recovery skeleton.
- **Phase 4 — Health vertical slice:** Health RAW -> semantic with contracts/DQ/reconciliation/recovery/SCD2.
- **Phase 5 — Transport streaming:** direct Snowpipe Streaming then Kafka Connector against the same RAW event contract.
- **Phase 6 — Pattern catalog:** load/SCD2/late-data/dedup/replay/backfill/schema evolution.
- **Phase 7 — Production hardening:** governance/cost/drift/alerts/recovery drills/SLO reporting.
- **Phase 8 — Openflow:** SQL Server -> Openflow CDC -> Health RAW without downstream redesign.

## 26. Current source/static-CI status

Completed/proven:

- [x] Terraform/provider pinning + lock files.
- [x] organization/identity/routine state separation.
- [x] Azure Blob + S3 backend adapters.
- [x] environment × domain databases and stable schemas.
- [x] human domain GUEST/READER/DEVELOPER/ADMIN RBAC.
- [x] metadata-driven warehouse grants.
- [x] DEV personal CREATE SCHEMA capability.
- [x] machine-only CI role/database-role/warehouse boundary.
- [x] DEV project-CI OIDC service-identity root.
- [x] framework workspace/query-tag utilities + tests.
- [x] project/dataset/RAW JSON Schemas + validator + tested example.
- [x] pinned reusable PR workspace workflow + Health/Transport wrappers.
- [x] cost-attribution diagnostic SQL.
- [x] canonical `CURRENT_CONTEXT.md` handoff.

Still required before Phase 1 exit:

- [ ] real Azure Blob or S3 control-plane state + GitHub OIDC trust;
- [ ] Snowflake DEV/UAT/PROD account bootstrap/import;
- [ ] live `identity/dev` apply;
- [ ] live DEV plan/apply/effective-grant verification;
- [ ] live `project-identity/dev` apply;
- [ ] configure Health/Transport GitHub Environment `ci` and run real PR create/drop;
- [ ] narrow live cost-history access + query verification;
- [ ] UAT proof before protected PROD;
- [ ] resource monitors/budgets/tagging hardening where live account/edition boundaries permit.

## 27. ADR index

```text
ADR-001  five-repository architecture
ADR-003  capability account roles + database roles
ADR-004  selective Terraform / one object owner
ADR-006  metadata-driven technical behaviour
ADR-007  RAW contract boundary
ADR-017  shared apply requires remote state + workload identity
ADR-018  three-account topology
ADR-019  environment × domain database boundary
ADR-020  domain GUEST + workload warehouses
ADR-021  isolated ORGADMIN bootstrap
ADR-022  S3-only backend — superseded
ADR-023  platform Terraform GitHub OIDC identity
ADR-024  Azure Blob/S3 backend adapters
ADR-025  DEV personal + PR CI workspace lifecycle
ADR-026  query-tag + cost-attribution contract
ADR-027  project PR-CI OIDC identity lifecycle
ADR-028  project/dataset/RAW metadata contracts
```

## 28. Immediate next source work

Without live cloud/Snowflake accounts:

```text
1. dbt environment/database/schema resolution primitives
2. reusable project metadata validation workflow + thin Health/Transport callers
3. thin DEV -> PR CI -> UAT -> PROD delivery contracts
4. first approved load strategy implementation/tests
```

Do not start Kafka, Snowpipe Streaming or Openflow before these foundations are proven.
