# Enterprise Snowflake Platform — Current Context

> **Purpose:** Fast handoff for a new conversation/session. Read this file first, then `PROJECT_BLUEPRINT.md` for long-term architecture.
>
> **Updated:** 2026-08-29
>
> **Current phase:** Phase 1 — Platform Foundation in progress.

## 1. Core rules

- Common technical behaviour is metadata-driven; genuine domain/business logic stays explicit SQL/code.
- Do not create a YAML programming language.
- No DEV/UAT/PROD Git branches; promote immutable Git SHA.
- One Snowflake object has one authoritative lifecycle owner.
- Git is configuration source of truth; `PLATFORM_CONTROL` is runtime/operational state.
- Human identity and machine identity are separate.
- Recoverability, reconciliation, freshness, observability and cost attribution are first-class.
- Do not start Kafka, Snowpipe Streaming or Openflow before platform/framework foundations are proven.

## 2. Repositories

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

Ownership:

- **platform-infra** — accounts/platform Terraform, RBAC, warehouses, state/WIF, workspace access, cost/governance/control-plane foundation;
- **data-project-framework** — reusable technical mechanics, metadata contracts/validation, workspace/query-tag utilities, reusable workflows;
- **demo-source-systems** — deterministic external-style source simulation only;
- **health/transport analytics** — domain contracts/config/business SQL/tests/semantic/ingestion config.

## 3. Snowflake topology

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

CI is not a fourth account.

Database = environment × governed domain, not physical source. Stable schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Published schemas initially: `MARTS`, `SEMANTIC`. RAW source-purpose schemas appear only on real source onboarding.

## 4. Human RBAC and employee membership

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

Stable database roles:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
  -> READ
  -> WRITE
  -> OWNER
```

Policy:

- GUEST = authenticated MARTS/SEMANTIC read-only;
- READER = all stable-layer read;
- DEV DEVELOPER = WRITE + transform compute;
- UAT/PROD DEVELOPER = read-only by default;
- Health authority never implies Transport authority.

Terraform defines roles/privileges. Entra ID / Okta / SCIM controls employee membership. Adding/removing an employee from an existing domain must not require Terraform.

## 5. Warehouses

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
WH_PLATFORM_OPS
```

Project metadata in each environment declares query/transform/CI warehouse keys. Root Terraform derives grants from metadata rather than hard-coding Health/Transport pairs.

## 6. DEV personal workspace

Human domain roles attach to `DEV_<DOMAIN>`, never `CI_<DOMAIN>`.

DEV WRITE receives `CREATE SCHEMA` on the matching DEV database.

```text
<DEVELOPER>_<LAYER>
```

Example: `DEV_HEALTH.ALICE_SMITH_STAGING`.

This is a namespace convention, **not** per-person security isolation; developers sharing the same domain developer role can require a separate personal-role design if stronger isolation is needed.

## 7. PR CI workspace and machine role

Machine-only DEV capability:

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> USAGE + CREATE SCHEMA on CI_<DOMAIN>
  -> USAGE on WH_<DOMAIN>_CI
```

Current examples:

```text
AR_HEALTH_CI
AR_TRANSPORT_CI
```

PR schema convention:

```text
PR_<NUMBER>_<LAYER>
```

Framework rendering creates transient PR schemas with zero-day Time Travel and prefix-guarded cleanup.

## 8. Project PR-CI Snowflake identities — implemented in source

A separate lifecycle now exists **after** the DEV platform stack:

```text
identity/dev
  -> platform/dev
      -> project-identity/dev
```

New Terraform root:

```text
terraform/stacks/project-identity/dev/
```

It uses generic `terraform/modules/service-identity/` to create a WIF service user bound to an **existing** CI role. It does not create/expand the role and gives no account-level privileges.

Derived identities:

```text
SU_GITHUB_HEALTH_CI
  -> AR_HEALTH_CI
  subject repo:ruizengalways/enterprise-snowflake-health-analytics:environment:ci

SU_GITHUB_TRANSPORT_CI
  -> AR_TRANSPORT_CI
  subject repo:ruizengalways/enterprise-snowflake-transport-analytics:environment:ci
```

Both use the DEV account-scoped Snowflake OIDC audience. Service users use `prevent_destroy`.

This root is statically Terraform-validated but has **not** been applied to live Snowflake.

See ADR-027.

## 9. Terraform lifecycle/state boundaries

There are now eight independent roots/state objects:

```text
organization
identity/dev
identity/uat
identity/prod
platform/dev
project-identity/dev
platform/uat
platform/prod
```

Source roots:

```text
terraform/stacks/organization/
terraform/stacks/identity/{dev,uat,prod}/
terraform/stacks/dev/
terraform/stacks/project-identity/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

Reference state key added for project identity:

```text
enterprise-snowflake-platform-infra/project-identity/dev/terraform.tfstate
```

Platform Terraform identities remain:

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Routine Terraform privileges:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine Terraform does not activate ACCOUNTADMIN/SYSADMIN/SECURITYADMIN. Identity bootstrap roots may use ACCOUNTADMIN only for machine-identity establishment. Organization root alone uses ORGADMIN.

Versions:

```text
Terraform CLI                 1.16.0
Snowflake Terraform provider  2.19.0
```

## 10. Remote state

Snowflake is not AWS-dependent.

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

Runtime adapter:

```text
terraform/backend-profiles/azurerm/backend.tf
terraform/backend-profiles/s3/backend.tf
terraform/scripts/select-backend.sh
```

OneDrive/SharePoint may store docs/runbooks/audit evidence, not authoritative live Terraform state. One deployment chooses one writable state backend.

## 11. Framework executable baseline

Current framework code includes:

```text
src/enterprise_snowflake_framework/
├── workspaces.py
├── query_tags.py
└── metadata_validation.py

project_schema/
├── project.schema.json
├── dataset.schema.json
└── raw_contract.schema.json

validation/validate_metadata.py
scripts/render_workspace_sql.py
scripts/render_query_tag.py
examples/minimal-project/
.github/workflows/framework-ci.yml
.github/workflows/pr-workspace.yml
```

### Workspace/query tag

Workspace code validates identifiers, renders personal/PR names, transient PR create SQL and prefix-guarded cleanup.

Query-tag required keys:

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

The builder rejects unsupported keys and values over Snowflake's 2000-character QUERY_TAG limit and can render `ALTER SESSION SET QUERY_TAG`.

### Metadata contracts

Version 1 schemas now validate:

```text
project
  code / name / repository / owner_team

dataset
  raw_contract / load_strategy / implementation
  business_key / watermark / freshness / reconciliation

RAW contract
  source_system / entity / grain / business_key
  columns/types/nullability/classification
  source_timestamp / snapshot|append|cdc semantics
  cadence / retention / breaking_change_policy
```

Semantic checks include duplicate dataset ids/columns, RAW contract reference containment/existence, keyed-strategy business keys, freshness threshold order, declared business/source timestamp columns, and required CDC operation/sequence columns.

Metadata deliberately does **not** encode business joins, calculations, arbitrary SQL or workflow branching.

See ADR-028.

## 12. Reusable PR workspace workflow — implemented in source

Framework workflow:

```text
.github/workflows/pr-workspace.yml
```

Thin callers now exist in:

```text
enterprise-snowflake-health-analytics/.github/workflows/pr-workspace.yml
enterprise-snowflake-transport-analytics/.github/workflows/pr-workspace.yml
```

Both pin framework commit:

```text
7ffafbc83ec7da154f036613541bf34b8a913e1a
```

Lifecycle:

```text
PR opened/reopened/synchronize -> create idempotent PR_<n>_* workspace
PR closed                      -> drop only PR_<n>_* workspace
```

The reusable workflow:

- targets GitHub Environment `ci` so the OIDC subject matches the project service user;
- validates project/action inputs;
- installs the pinned framework;
- renders QUERY_TAG + workspace SQL;
- installs Snowflake CLI `3.25.0` using Snowflake's action pinned to commit `1160898243c351349621a6c2bac2e455ab1077b2` (release v3.3.1);
- manually requests a GitHub OIDC token using the **account-scoped** Snowflake audience;
- authenticates as `SU_GITHUB_<DOMAIN>_CI` with `AR_<DOMAIN>_CI`;
- runs `snow connection test -x` then `snow sql --local-only --enhanced-exit-codes -f ...`;
- currently executes only framework-generated workspace SQL, not untrusted PR business code.

Why manual OIDC token request: Snowflake's first-party action currently uses shared `snowflakecomputing.com` when `use-oidc: true`, while this platform intentionally requires account-scoped audiences.

This workflow is source/CI-validated only; no live `ci` GitHub Environment/Snowflake service identity exists yet, so no real PR schema has been created.

## 13. Cost attribution baseline

```text
Domain storage/recovery         -> <ENVIRONMENT>_<DOMAIN>
Compute                         -> WH_<DOMAIN>_<WORKLOAD>
Per-query execution attribution -> QUERY_TAG + QUERY_ATTRIBUTION_HISTORY
Warehouse idle compute          -> WAREHOUSE_METERING_HISTORY
Serverless/ingestion            -> service-specific usage histories
Fine storage detail             -> Snowflake storage metrics/history
```

Baseline diagnostic SQL:

```text
snowflake/monitoring/queries/cost_attribution.sql
```

Query-attributed compute excludes idle time; do not label it the full warehouse bill.

## 14. Verified CI status

Latest Terraform run proving project identity root:

```text
Run:    33223588208
Commit: 509f2986dd9b74f063e7f65b4dfcf8d7655cf5ed
Result: SUCCESS
```

Passed:

```text
fmt + backend selector syntax
organization
identity/dev
identity/uat
identity/prod
dev
project-identity/dev
uat
prod
backend azurerm
backend s3
```

Latest framework run proving metadata contracts + reusable workflow commit:

```text
Run:    33223835181
Commit: 7ffafbc83ec7da154f036613541bf34b8a913e1a
Result: SUCCESS
```

Static CI proves source/provider/schema/tests; it does not prove live Snowflake authorization or cloud connectivity.

## 15. What has NOT happened yet

Do not claim these are complete:

- no real Azure Blob/S3 state control plane provisioned;
- no Snowflake DEV/UAT/PROD account bootstrap/import executed;
- no Terraform identity root applied to live Snowflake;
- no real DEV remote plan/apply;
- no `project-identity/dev` live apply;
- GitHub Environment `ci` values are not configured/tested;
- no real PR workspace create/drop executed in Snowflake;
- live effective grants remain unverified;
- no UAT/PROD project deployment identities;
- no persisted cost views/resource monitors/budgets;
- no project dbt load/SCD2 implementation.

## 16. Next source work without live accounts

```text
1. dbt environment/database/schema resolution primitives
2. connect metadata validator as reusable project CI validation
3. define thin DEV -> PR CI -> UAT -> PROD workflow contracts
4. start framework basic load strategy implementation/tests
```

When real infrastructure is available:

```text
choose Azure Blob OR S3
-> provision state/OIDC
-> organization bootstrap/import
-> identity/dev apply
-> platform/dev plan/apply/verify
-> project-identity/dev apply
-> configure project GitHub Environment ci
-> real PR workspace create/drop test
-> UAT
-> protected PROD
```

## 17. Important ADRs

```text
ADR-018  three-account topology
ADR-019  environment × domain database boundary
ADR-020  domain GUEST + workload warehouses
ADR-021  isolated ORGADMIN bootstrap
ADR-022  old S3-only choice — superseded
ADR-023  GitHub OIDC Terraform identity
ADR-024  Azure Blob/S3 backend adapters
ADR-025  DEV personal + PR CI workspace lifecycle
ADR-026  query-tag + cost-attribution contract
ADR-027  project PR-CI OIDC identity lifecycle
ADR-028  project/dataset/RAW metadata contracts
```

## 18. Deferred technology

```text
Kafka Connector
Snowpipe Streaming
Openflow
broad domain dbt modelling
full governance policies
full observability dashboards
production rollback automation
```
