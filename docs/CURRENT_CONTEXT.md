# Enterprise Snowflake Platform — Current Context

> **Purpose:** Fast handoff for a new conversation/session. Read this file first, then `PROJECT_BLUEPRINT.md` for the long-term architecture.
>
> **Updated:** 2026-08-29
>
> **Current phase:** Phase 1 — Platform Foundation in progress.

## 1. Project intent

Build a production-grade, reusable enterprise Snowflake platform/reference implementation with practical platform engineering and data engineering patterns.

Key principles:

- metadata drives stable technical behaviour; genuine domain/business differences remain explicit code;
- do not over-abstract into a YAML programming language;
- one Git history, no DEV/UAT/PROD branches;
- promote immutable Git SHA through environments;
- one Snowflake object has one authoritative lifecycle owner;
- human identity and machine deployment identity are separate;
- recoverability, reconciliation, freshness, observability and cost attribution are first-class concerns;
- do not introduce Kafka/Snowpipe Streaming/Openflow/broad dbt modelling before the platform/framework foundation is ready.

## 2. Repository model

Canonical repositories:

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

Responsibilities:

- **platform-infra** — Snowflake accounts/platform Terraform, RBAC, warehouses, state/identity contract, governance/control-plane foundations;
- **data-project-framework** — reusable dbt/macros/tests/metadata validation/delivery patterns;
- **demo-source-systems** — deterministic external-style source generation/delivery only;
- **health-analytics** — Health contracts/config/business SQL/tests/semantic/ingestion config;
- **transport-analytics** — Transport contracts/config/business SQL/tests/semantic/streaming config.

Thin project repos consume versioned shared framework logic; shared mechanics are not copied into each domain repo.

## 3. Snowflake account topology

Canonical topology uses three Snowflake accounts:

```text
Snowflake Organization
│
├── DEV account
│   ├── DEV_HEALTH
│   ├── CI_HEALTH
│   ├── DEV_TRANSPORT
│   ├── CI_TRANSPORT
│   └── PLATFORM_CONTROL
│
├── UAT account
│   ├── UAT_HEALTH
│   ├── UAT_TRANSPORT
│   └── PLATFORM_CONTROL
│
└── PROD account
    ├── PROD_HEALTH
    ├── PROD_TRANSPORT
    └── PLATFORM_CONTROL
```

CI is not a fourth account. PR CI stays in DEV but uses separate `CI_<DOMAIN>` databases and `WH_<DOMAIN>_CI` compute.

## 4. Database / schema boundary

Database pattern:

```text
<ENVIRONMENT>_<DOMAIN>
```

A database is environment × governed data product/domain. Do **not** create one database per physical MSSQL/MySQL/API source just for chargeback.

Stable schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Published schemas initially:

```text
MARTS
SEMANTIC
```

RAW schemas are added only when a real source is onboarded, e.g. `RAW_EHR_MSSQL` or `RAW_VEHICLE_API`.

Personal DEV schema pattern inside `DEV_<DOMAIN>`:

```text
<DEVELOPER>_<LAYER>
```

PR CI schema pattern inside `CI_<DOMAIN>`:

```text
PR_<NUMBER>_<LAYER>
```

Personal/PR schema lifecycle is intentionally outside long-lived Terraform state and is not implemented yet.

## 5. Domain RBAC

Every domain gets independent account roles:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

Every domain database gets only its owning domain's database roles:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
  -> DR_<DOMAIN>_ANALYTICS_READ
  -> DR_<DOMAIN>_ANALYTICS_WRITE
  -> DR_<DOMAIN>_ANALYTICS_OWNER
```

`GUEST` is authenticated read-only consumer access to published schemas only (`MARTS`, `SEMANTIC`). It is not Snowflake `PUBLIC` and not anonymous access.

`READER` can inspect all stable layers. DEV developers receive WRITE. UAT/PROD developers remain read-only by default.

Health roles do not imply Transport access and vice versa.

## 6. Employee identity rule

Terraform manages **what roles/privileges/warehouses exist**, not day-to-day employee membership.

Target enterprise flow:

```text
Employee / contractor
    -> Entra ID / Okta group
        -> SCIM / approved identity provisioning
            -> AR_<DOMAIN>_<CAPABILITY>
```

Examples:

```text
SNOWFLAKE_FINANCE_GUEST     -> AR_FINANCE_GUEST
SNOWFLAKE_FINANCE_READER    -> AR_FINANCE_READER
SNOWFLAKE_FINANCE_DEVELOPER -> AR_FINANCE_DEVELOPER
```

Adding Alice to an existing Finance domain should not require Alice or her manager to know Terraform.

When a **new domain** is created, platform Terraform provisions its standard databases, roles, database roles and warehouses once. Subsequent employee joins/leaves are identity-governance operations.

## 7. Domain compute

Per-domain warehouse pattern:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
```

Current examples:

```text
WH_HEALTH_QUERY
WH_HEALTH_TRANSFORM
WH_HEALTH_CI
WH_TRANSPORT_QUERY
WH_TRANSPORT_TRANSFORM
WH_TRANSPORT_CI
WH_PLATFORM_OPS
```

GUEST receives QUERY; READER inherits it. DEV DEVELOPER additionally receives TRANSFORM. UAT/PROD ADMIN currently has TRANSFORM as a transitional human path until project deployment identities are implemented. CI warehouses are machine-only.

This separation is also a primary compute cost-attribution boundary.

## 8. Terraform lifecycle roots

There are seven independent lifecycle roots/state boundaries:

```text
terraform/stacks/organization/
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

Meaning:

- `organization/` — ORGADMIN-only Snowflake account bootstrap/import;
- `identity/<env>/` — privileged bootstrap of Terraform machine identity;
- `dev/uat/prod` — routine Snowflake platform resources.

Every root pins Terraform/Snowflake provider versions and commits `.terraform.lock.hcl`.

Current baseline:

```text
Terraform CLI                 1.16.0
Snowflake Terraform provider  2.19.0
```

## 9. Snowflake Terraform machine identity

Per account:

```text
DEV   SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
UAT   SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
PROD  SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

GitHub OIDC subjects are pinned to repository + GitHub Environment:

```text
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:dev
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:uat
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:prod
```

Routine Terraform role baseline privileges:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine Terraform does not activate ACCOUNTADMIN, SYSADMIN or SECURITYADMIN.

Identity bootstrap may use ACCOUNTADMIN only to create the dedicated machine identity. The Snowflake service users and machine roles use `prevent_destroy`.

## 10. Terraform state — current canonical decision

The Snowflake platform is **not AWS-dependent**.

Supported remote-state profiles:

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS reference)
```

The same Snowflake Terraform root code is used in either case.

Terraform backend type cannot be selected through a Terraform input variable, so execution uses:

```text
terraform/backend-profiles/azurerm/backend.tf
terraform/backend-profiles/s3/backend.tf
terraform/scripts/select-backend.sh
```

to materialise an ignored `<root>/backend.generated.tf` immediately before remote `terraform init`.

### Microsoft/Azure reference

```text
GitHub OIDC
    -> Microsoft Entra workload federation
        -> Azure Blob Terraform state
```

Use Entra/OIDC rather than a long-lived client secret. Baseline data-plane access is `Storage Blob Data Contributor` scoped to the state container.

### AWS reference

```text
GitHub OIDC
    -> AWS IAM
        -> S3 Terraform state + .tflock
```

S3 uses versioning, encryption, public-access blocking and Terraform native `use_lockfile = true`. New deployments do not add deprecated DynamoDB locking.

### OneDrive / SharePoint

OneDrive/SharePoint can hold architecture documents, runbooks, change records and audit evidence. It is **not** the authoritative live Terraform state backend.

Do not have S3 and Azure Blob both writable for the same state. A real deployment chooses one backend; changing it later is a controlled Terraform state migration.

## 11. State keys

Whichever backend is chosen, retain:

```text
enterprise-snowflake-platform-infra/organization/terraform.tfstate
enterprise-snowflake-platform-infra/identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/identity/uat/terraform.tfstate
enterprise-snowflake-platform-infra/identity/prod/terraform.tfstate
enterprise-snowflake-platform-infra/platform/dev/terraform.tfstate
enterprise-snowflake-platform-infra/platform/uat/terraform.tfstate
enterprise-snowflake-platform-infra/platform/prod/terraform.tfstate
```

## 12. CI / workflow status

Static CI validates:

```text
terraform fmt
organization
identity/dev
identity/uat
identity/prod
dev
uat
prod
```

and materialises/validates both backend declarations:

```text
azurerm
s3
```

without connecting to either cloud.

Latest verified static CI run:

```text
GitHub Actions run: 33222590387
Commit:             7d9b345ba21ccf34fe276b7906ba6a4a213775b6
Result:             SUCCESS
```

All ten jobs succeeded: formatting/selector syntax, all seven Terraform roots, Azure Blob backend profile and S3 backend profile.

`.github/workflows/terraform-plan-dev.yml` is manual-only and supports `TF_STATE_BACKEND=azurerm|s3`; empty defaults to `azurerm` as the Microsoft-first reference. It uses GitHub OIDC for the selected state backend and separately obtains a Snowflake OIDC token for WIF. It performs plan only, not apply.

## 13. What has NOT happened yet

Do not claim any of the following are complete:

- no real Azure Blob or S3 state control plane has been provisioned for this project yet;
- no real Snowflake DEV/UAT/PROD account bootstrap/import has been executed by this Terraform;
- no identity root has been applied to a real Snowflake account;
- no real remote DEV Terraform plan has been executed;
- no DEV/UAT/PROD platform apply has happened;
- Snowflake-side effective privileges/grants have not yet been verified against a live account;
- personal DEV / PR schema lifecycle is not implemented;
- cost controls/resource monitors/query-tag baseline are not completed.

Static `terraform validate` proves configuration/provider-schema validity, not real cloud access or real Snowflake authorization.

## 14. Next implementation order

When a real control-plane account is available:

```text
1. Choose one Terraform state backend for the deployment
   - Azure Blob OR S3
2. Provision the remote state control plane + GitHub OIDC trust
3. Bootstrap/import Snowflake DEV/UAT/PROD accounts under controlled ORGADMIN
4. Bootstrap identity/dev under controlled ACCOUNTADMIN
5. Configure GitHub Environment dev variables
6. Run the first real DEV remote plan
7. Review privilege gaps; add only demonstrated privileges
8. Apply DEV under review
9. Verify databases/schemas/roles/grants/warehouses from Snowflake
10. Implement personal/PR schema lifecycle + cost attribution baseline
11. Prove UAT
12. Only then enable protected PROD plan/apply
```

Do not start Transport streaming or Openflow during these steps.

## 15. New-domain onboarding target

For a future `FINANCE` domain, platform onboarding should derive standard resources such as:

```text
DEV_FINANCE
CI_FINANCE
UAT_FINANCE
PROD_FINANCE

AR_FINANCE_GUEST
AR_FINANCE_READER
AR_FINANCE_DEVELOPER
AR_FINANCE_ADMIN

DR_FINANCE_ANALYTICS_GUEST/READ/WRITE/OWNER

WH_FINANCE_QUERY
WH_FINANCE_TRANSFORM
WH_FINANCE_CI
```

This should become metadata-driven platform onboarding, without making source-specific business logic generic.

## 16. Important ADRs

```text
ADR-018  three-account DEV/UAT/PROD topology
ADR-019  environment × data-product database boundary
ADR-020  domain GUEST access + workload warehouses
ADR-021  isolated ORGADMIN organization bootstrap
ADR-022  historical S3-only state choice — superseded
ADR-023  GitHub OIDC Snowflake Terraform identity
ADR-024  cloud-agnostic Azure Blob/S3 state backend profiles
```

## 17. Deferred technology

Remain intentionally deferred until foundations are proven:

```text
Kafka Connector
Snowpipe Streaming
Openflow
broad dbt modelling
full governance policies
full observability dashboards
production rollback automation
```

Transport will later compare direct Snowpipe Streaming and Kafka Connector against the same logical RAW event contract. Health will add Openflow later without forcing downstream redesign.
