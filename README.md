# Enterprise Snowflake Platform Infrastructure

Central platform-engineering repository for the Enterprise Snowflake reference platform.

## Start here

For a new ChatGPT/session handoff, read in this order:

1. [`docs/CURRENT_CONTEXT.md`](docs/CURRENT_CONTEXT.md) — current implementation state, decisions, blockers and next actions.
2. [`docs/PROJECT_BLUEPRINT.md`](docs/PROJECT_BLUEPRINT.md) — canonical long-term architecture.
3. [`docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`](docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md) — state/WIF execution model.
4. [`docs/architecture/ACCOUNT_TOPOLOGY.md`](docs/architecture/ACCOUNT_TOPOLOGY.md)
5. [`docs/architecture/RBAC_MODEL.md`](docs/architecture/RBAC_MODEL.md)
6. [`docs/architecture/REPOSITORY_LAYOUT.md`](docs/architecture/REPOSITORY_LAYOUT.md)
7. [`docs/standards/TERRAFORM_STANDARDS.md`](docs/standards/TERRAFORM_STANDARDS.md)
8. [`docs/runbooks/terraform-platform-bootstrap.md`](docs/runbooks/terraform-platform-bootstrap.md)

Architecture decisions are under `docs/adr/`.

## This repository owns

- Snowflake organization/account foundation and privileged account bootstrap
- DEV / UAT / PROD account topology
- domain analytics databases and stable structural schemas
- domain/platform RBAC and database-role design
- domain workload warehouses and cost-control foundations
- GitHub OIDC / Snowflake workload identities for platform Terraform
- Terraform remote-state adapter contract and deployment guardrails
- `PLATFORM_CONTROL` structural/operational foundation
- governance, observability and recovery platform architecture

## This repository does not own

- Health or Transport business transformations
- project-specific dbt models
- reusable dbt framework logic owned by `enterprise-snowflake-data-project-framework`
- source-system simulation
- human employee lifecycle records that should come from enterprise identity/SSO/SCIM
- Metric Guard

## Terraform foundation

```text
terraform/
├── backend-profiles/
│   ├── azurerm/
│   └── s3/
├── scripts/
│   └── select-backend.sh
├── modules/
│   ├── analytics-environment/
│   ├── warehouse/
│   ├── platform-control/
│   ├── rbac/
│   └── workload-identity/
└── stacks/
    ├── organization/
    ├── identity/
    │   ├── dev/
    │   ├── uat/
    │   └── prod/
    ├── dev/
    ├── uat/
    └── prod/
```

Configuration:

```text
config/organization.yml
config/environments/dev.yml
config/environments/uat.yml
config/environments/prod.yml
```

`organization/` alone uses ORGADMIN for Snowflake account creation/import. `identity/<env>/` roots are separate privileged bootstraps for GitHub OIDC service users and `AR_TERRAFORM_<ENV>` roles. Routine DEV/UAT/PROD roots use those dedicated machine roles rather than ACCOUNTADMIN, SYSADMIN or SECURITYADMIN.

Every Terraform root commits `.terraform.lock.hcl`. Static CI validates all seven roots in read-only lock mode and separately validates both backend profiles.

## State and machine authentication

Terraform state is intentionally independent of Snowflake authentication.

Supported state profiles:

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS reference)
```

The same Snowflake root code is used for either backend. `terraform/scripts/select-backend.sh` materialises an ignored `backend.generated.tf` only at execution time.

For Microsoft-centred enterprises, the reference path is:

```text
GitHub OIDC -> Microsoft Entra workload federation -> Azure Blob state
GitHub OIDC -> Snowflake WIF -> SU_GITHUB_TERRAFORM_<ENV> -> AR_TERRAFORM_<ENV>
```

For AWS-centred enterprises, the state branch becomes GitHub OIDC -> AWS IAM -> S3 while the Snowflake branch is unchanged.

OneDrive/SharePoint can store architecture documents, runbooks and audit evidence; they are not the live Terraform state backend.

Seven state lifecycle boundaries are retained: organization, identity/dev, identity/uat, identity/prod, platform/dev, platform/uat and platform/prod.

A manual-only [`terraform-plan-dev.yml`](.github/workflows/terraform-plan-dev.yml) supports Azure Blob or S3 and intentionally performs no apply.

## Domain access and compute

Database boundary is environment × domain, for example `DEV_HEALTH`, `CI_HEALTH`, `UAT_TRANSPORT` and `PROD_TRANSPORT`. Physical source systems do not each receive a database merely for cost attribution.

Every domain receives:

```text
AR_<DOMAIN>_GUEST -> READER -> DEVELOPER -> ADMIN
DR_<DOMAIN>_ANALYTICS_GUEST -> READ -> WRITE -> OWNER
```

`GUEST` is authenticated read-only access to published schemas (`MARTS`, `SEMANTIC`) only. `READER` can inspect all stable domain layers.

Domain compute is separated by workload:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
```

Employees are assigned to domain roles through the enterprise identity system; Terraform defines the roles/privileges/warehouses, not employee membership.

## Current phase

**Phase 1 — Platform Foundation is in progress.**

Proven in source/static CI: pinned Terraform/provider versions and lock files, organization bootstrap, per-account identity bootstrap roots, Azure Blob and S3 backend adapters, GitHub OIDC/Snowflake WIF service-user configuration, dedicated `AR_TERRAFORM_<ENV>` roles, three-account/domain infrastructure, GUEST/READER/DEVELOPER/ADMIN RBAC, workload warehouses, seven-root validation and backend-profile validation.

Still required before Phase 1 exit: provision one real remote-state control plane (Azure Blob or S3), execute/import Snowflake organization and identity bootstraps, configure GitHub Environments, run/review the first real DEV remote plan/apply, verify privileges and objects inside Snowflake, then prove UAT before protected PROD automation. Personal/PR schema lifecycle and cost-control hardening also remain.

Kafka, Snowpipe Streaming, Openflow and broad dbt modelling remain intentionally deferred.
