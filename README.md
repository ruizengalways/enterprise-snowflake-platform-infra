# Enterprise Snowflake Platform Infrastructure

Central platform-engineering repository for the Enterprise Snowflake reference platform.

## Canonical architecture

- [`docs/PROJECT_BLUEPRINT.md`](docs/PROJECT_BLUEPRINT.md)
- [`docs/architecture/REPOSITORY_LAYOUT.md`](docs/architecture/REPOSITORY_LAYOUT.md)
- [`docs/architecture/ACCOUNT_TOPOLOGY.md`](docs/architecture/ACCOUNT_TOPOLOGY.md)
- [`docs/architecture/RBAC_MODEL.md`](docs/architecture/RBAC_MODEL.md)
- [`docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`](docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md)
- [`docs/standards/NAMING_CONVENTIONS.md`](docs/standards/NAMING_CONVENTIONS.md)
- [`docs/standards/TERRAFORM_STANDARDS.md`](docs/standards/TERRAFORM_STANDARDS.md)
- [`docs/runbooks/terraform-platform-bootstrap.md`](docs/runbooks/terraform-platform-bootstrap.md)

Architecture decisions are under `docs/adr/`.

## This repository owns

- Snowflake organization/account foundation and privileged account bootstrap
- DEV / UAT / PROD account topology
- domain analytics databases and stable structural schemas
- domain/platform RBAC and database-role design
- domain workload warehouses and cost-control foundations
- GitHub OIDC / Snowflake workload identities for platform Terraform
- Terraform remote-state contract and deployment guardrails
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

`organization/` alone uses ORGADMIN for Snowflake account creation/import. The three `identity/<env>/` roots are separate privileged bootstraps for GitHub OIDC service users and `AR_TERRAFORM_<ENV>` roles. Routine DEV/UAT/PROD roots use those dedicated machine roles rather than `ACCOUNTADMIN`, `SYSADMIN`, or `SECURITYADMIN`.

Every Terraform root commits `.terraform.lock.hcl`. Static CI currently validates all seven roots using lock files in read-only mode.

## State and machine authentication

The reference backend is Amazon S3 with encrypted state and native S3 lockfiles (`use_lockfile = true`). State is split into seven lifecycle objects: organization, identity/dev, identity/uat, identity/prod, platform/dev, platform/uat and platform/prod.

The state bucket is an external control-plane prerequisite with versioning, encryption, blocked public access and narrowly scoped IAM. GitHub accesses state through AWS OIDC; no static AWS access key is part of the design.

Snowflake routine Terraform uses:

```text
GitHub Environment dev  -> SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
GitHub Environment uat  -> SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
GitHub Environment prod -> SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

The Snowflake OIDC subject is pinned to repository + GitHub Environment. The audience is account-scoped and supplied as deployment configuration rather than using the shared `snowflakecomputing.com` audience.

A manual-only [`terraform-plan-dev.yml`](.github/workflows/terraform-plan-dev.yml) now defines the first secretless remote-plan path. It requires real AWS/Snowflake environment configuration and intentionally performs no apply.

## Domain access and compute

Database boundary is environment × domain, for example `DEV_HEALTH`, `CI_HEALTH`, `UAT_TRANSPORT`, and `PROD_TRANSPORT`. Physical source systems do not each receive a database merely for cost attribution.

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

This gives Health, Transport and future domains independent access and compute/cost boundaries without creating database-per-source.

## Current phase

**Phase 1 — Platform Foundation is in progress.**

Proven in source/static CI: pinned Terraform/provider versions and lock files, organization bootstrap, separate per-account identity bootstrap roots, S3 backend contract, GitHub OIDC/Snowflake WIF service-user configuration, dedicated `AR_TERRAFORM_<ENV>` routine roles, three-account/domain infrastructure, GUEST/READER/DEVELOPER/ADMIN RBAC, workload warehouses, and `fmt/init/validate` across all seven Terraform roots.

Still required before Phase 1 exit: provision/configure the real S3 state control plane and AWS OIDC IAM role, execute/import Snowflake organization and identity bootstraps, configure GitHub Environment variables, run/review the first real DEV remote plan/apply, verify privileges and objects inside Snowflake, then prove UAT before protected PROD automation. Personal/PR schema lifecycle and cost-control hardening also remain.

Kafka, Snowpipe Streaming, Openflow and broad dbt modelling remain intentionally deferred.
