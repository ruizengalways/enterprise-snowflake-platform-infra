# Enterprise Snowflake Platform — Current Context

> **Purpose:** Fast handoff for a new conversation/session. Read this file first, then `PROJECT_BLUEPRINT.md` for long-term architecture.
>
> **Updated:** 2026-08-29
>
> **Current phase:** Phase 1 — Platform Foundation in progress.

## 1. Core intent and rules

Build a production-grade reusable Snowflake platform/reference implementation.

Canonical principles:

- common technical behaviour is metadata-driven; genuine domain/business logic stays explicit code;
- do not create a YAML programming language;
- one Git history, no DEV/UAT/PROD environment branches;
- promote immutable Git SHA;
- one Snowflake object has one authoritative lifecycle owner;
- Git is configuration source of truth; `PLATFORM_CONTROL` is runtime/operational state;
- human identity and machine identity are separate;
- recoverability, reconciliation, freshness, observability and cost attribution are first-class;
- do not start Kafka/Snowpipe Streaming/Openflow/broad dbt modelling before platform/framework foundations are proven.

## 2. Repositories

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

Ownership:

- **platform-infra** — Snowflake account/platform Terraform, RBAC, warehouses, state/WIF, workspace access boundary, cost/governance/control-plane foundation;
- **data-project-framework** — reusable dbt/framework mechanics, metadata validation, workspace lifecycle helpers, query-tag utilities, reusable workflows;
- **demo-source-systems** — deterministic external-style source simulation only;
- **health-analytics / transport-analytics** — domain contracts/config/business SQL/tests/semantic/ingestion configuration.

## 3. Snowflake account / database topology

```text
Snowflake Organization
│
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

Published schemas initially: `MARTS`, `SEMANTIC`.

RAW source-purpose schemas are created only when a real source is onboarded.

## 4. Human RBAC

Every domain:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

Stable domain databases:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
  -> DR_<DOMAIN>_ANALYTICS_READ
  -> DR_<DOMAIN>_ANALYTICS_WRITE
  -> DR_<DOMAIN>_ANALYTICS_OWNER
```

Policy:

- GUEST = authenticated read-only on MARTS/SEMANTIC only;
- READER = read all stable layers;
- DEV DEVELOPER = WRITE + transform compute;
- UAT/PROD DEVELOPER = read-only by default;
- UAT/PROD ADMIN temporarily has transform compute until project deployment identities exist;
- Health authority never implies Transport authority.

Terraform defines roles/privileges; Entra ID / Okta / SCIM controls employee membership. Adding/removing an employee from an existing domain should not require Terraform.

## 5. Domain warehouses

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
WH_PLATFORM_OPS
```

Environment project metadata now contains each domain's query/transform/CI warehouse keys. Root Terraform derives grants from metadata; it no longer hard-codes separate Health/Transport grant blocks.

This is important for future `FINANCE` onboarding.

## 6. DEV personal workspaces

Human domain RBAC in the DEV account attaches only to `DEV_<DOMAIN>`, not `CI_<DOMAIN>`.

DEV `DR_<DOMAIN>_ANALYTICS_WRITE` receives `CREATE SCHEMA` on the matching `DEV_<DOMAIN>` database.

Personal schema convention:

```text
<DEVELOPER>_<LAYER>
```

Example:

```text
DEV_HEALTH.ALICE_SMITH_STAGING
```

This is a workspace namespace, **not** a per-person security boundary, because developers share the domain developer role. Stronger personal isolation would require an identity-governed personal-role design.

## 7. PR CI workspaces

Human GUEST/READER/DEVELOPER/ADMIN roles do **not** attach to `CI_<DOMAIN>` databases.

DEV Terraform now creates machine-only CI capabilities:

```text
AR_HEALTH_CI
  -> CI_HEALTH.DR_HEALTH_CI_WORKSPACE
      -> USAGE + CREATE SCHEMA on CI_HEALTH
  -> WH_HEALTH_CI

AR_TRANSPORT_CI
  -> CI_TRANSPORT.DR_TRANSPORT_CI_WORKSPACE
      -> USAGE + CREATE SCHEMA on CI_TRANSPORT
  -> WH_TRANSPORT_CI
```

PR schema convention:

```text
PR_<NUMBER>_<LAYER>
```

The shared framework implements guarded naming/create/drop SQL. PR schemas are rendered as transient with zero-day Time Travel and must be explicitly dropped when the PR lifecycle ends.

A real GitHub OIDC **project-CI service identity** that receives `AR_<DOMAIN>_CI` is still pending; the stable Snowflake role boundary is implemented now.

See ADR-025.

## 8. Framework executable baseline

`enterprise-snowflake-data-project-framework` now contains its first real code:

```text
pyproject.toml
src/enterprise_snowflake_framework/workspaces.py
src/enterprise_snowflake_framework/query_tags.py
scripts/render_workspace_sql.py
scripts/render_query_tag.py
tests/
.github/workflows/framework-ci.yml
docs/patterns/workspaces-and-query-tags.md
```

Workspace renderer:

- normalises developer tokens safely;
- produces personal and PR schema names;
- validates unquoted Snowflake identifiers;
- PR create uses `CREATE TRANSIENT SCHEMA ... DATA_RETENTION_TIME_IN_DAYS = 0`;
- cleanup refuses schemas outside the expected prefix.

Query-tag builder:

- required keys: `project`, `environment`, `workload`;
- optional: `source`, `pipeline`, `dataset`, `run_id`, `git_sha`, `pr_number`, `operation`;
- deterministic compact JSON;
- rejects unsupported keys;
- fails before Snowflake's 2000-character `QUERY_TAG` limit;
- can render `ALTER SESSION SET QUERY_TAG = ...`;
- query tags must not contain personal/sensitive/regulated/business payload data.

Latest verified framework CI:

```text
Run:    33223164318
Commit: ce92f6557991dfcc2a7a90f95e0b2f485e1be3b6
Result: SUCCESS
```

## 9. Cost attribution baseline

Canonical cost model is multi-dimensional:

```text
Domain storage/recovery        -> <ENVIRONMENT>_<DOMAIN>
Compute                        -> WH_<DOMAIN>_<WORKLOAD>
Per-query execution attribution-> QUERY_TAG + QUERY_ATTRIBUTION_HISTORY
Warehouse idle compute         -> WAREHOUSE_METERING_HISTORY
Serverless/ingestion           -> service-specific usage histories
Fine storage detail            -> Snowflake storage metrics/history
```

Query-attributed compute excludes idle warehouse time and must not be presented as the complete warehouse bill.

Source-controlled diagnostic SQL:

```text
snowflake/monitoring/queries/cost_attribution.sql
```

Standard:

```text
docs/standards/COST_ATTRIBUTION.md
```

Persisted cost views/resource monitors/budgets are still deferred until live Snowflake administrative/access boundaries are verified.

See ADR-026.

## 10. Terraform lifecycle / machine identity

Seven independent Terraform roots/state boundaries:

```text
terraform/stacks/organization/
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

Platform Terraform identities:

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Routine privileges currently:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine Terraform does not activate ACCOUNTADMIN/SYSADMIN/SECURITYADMIN. Identity bootstrap may use ACCOUNTADMIN only to establish the machine identity/WIF trust.

Versions:

```text
Terraform CLI                 1.16.0
Snowflake Terraform provider  2.19.0
```

## 11. Terraform remote state

Snowflake is not AWS-dependent.

Supported backend profiles:

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

It materialises ignored `backend.generated.tf` before remote init.

OneDrive/SharePoint may hold docs/runbooks/audit evidence, but not live Terraform state.

One real deployment chooses one writable backend; do not mirror the same state as writable in both Azure Blob and S3.

## 12. Platform Infra CI status

Static CI validates:

```text
terraform fmt + backend selector syntax
organization
identity/dev
identity/uat
identity/prod
dev
uat
prod
backend azurerm
backend s3
```

Latest verified Terraform run containing the workspace-access implementation:

```text
Run:    33223028453
Commit: 8bee3f89f10ca38040b4ad22f98539a48dd733d0
Result: SUCCESS
```

All jobs passed, including `validate dev` with the new workspace module.

Static validation proves HCL/provider-schema validity, not live Snowflake authorization.

## 13. What has NOT happened yet

Do not claim these are complete:

- no real Azure Blob or S3 state control plane is provisioned for this project;
- no Snowflake DEV/UAT/PROD account bootstrap/import has been executed by this Terraform;
- no identity root has been applied to a live account;
- no real remote DEV Terraform plan/apply has run;
- live effective Snowflake privileges/grants are unverified;
- no project PR-CI OIDC service user is bound to `AR_<DOMAIN>_CI` yet;
- no project deployment/promotion machine identities yet;
- no persisted cost views/resource monitors/budgets yet;
- no data-project dbt load/SCD2 implementation yet.

## 14. Next implementation order

Without live cloud/Snowflake accounts, next useful source work is:

```text
1. project-CI identity contract + reusable PR workspace workflow skeleton
2. generic project metadata schema/validation
3. environment/database/schema resolution primitives for dbt
4. thin CI/CD spine contracts (DEV -> PR CI -> UAT -> PROD)
```

When real control-plane infrastructure becomes available:

```text
1. choose Azure Blob OR S3
2. provision state + GitHub OIDC trust
3. bootstrap/import Snowflake accounts
4. bootstrap identity/dev
5. run real DEV plan
6. apply DEV under review
7. verify RBAC/workspaces/cost-access live
8. prove UAT
9. only then protected PROD
```

Do not start Transport streaming or Openflow before this foundation is proven.

## 15. Important ADRs

```text
ADR-018  three-account DEV/UAT/PROD topology
ADR-019  environment × domain database boundary
ADR-020  domain GUEST + workload warehouses
ADR-021  isolated ORGADMIN bootstrap
ADR-022  historical S3-only state choice — superseded
ADR-023  GitHub OIDC Terraform identity
ADR-024  Azure Blob/S3 backend adapters
ADR-025  DEV personal + PR CI workspace lifecycle
ADR-026  query-tag + cost-attribution contract
```

## 16. Deferred technology

```text
Kafka Connector
Snowpipe Streaming
Openflow
broad dbt modelling
full governance policies
full observability dashboards
production rollback automation
```
