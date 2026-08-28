# Enterprise Snowflake Platform Infrastructure

Central platform-engineering repository for the Enterprise Snowflake reference platform.

## Canonical architecture

- [`docs/PROJECT_BLUEPRINT.md`](docs/PROJECT_BLUEPRINT.md)
- [`docs/architecture/REPOSITORY_LAYOUT.md`](docs/architecture/REPOSITORY_LAYOUT.md)
- [`docs/architecture/ACCOUNT_TOPOLOGY.md`](docs/architecture/ACCOUNT_TOPOLOGY.md)
- [`docs/architecture/RBAC_MODEL.md`](docs/architecture/RBAC_MODEL.md)
- [`docs/standards/NAMING_CONVENTIONS.md`](docs/standards/NAMING_CONVENTIONS.md)
- [`docs/standards/TERRAFORM_STANDARDS.md`](docs/standards/TERRAFORM_STANDARDS.md)

Architecture decisions are under `docs/adr/`.

## This repository owns

- Snowflake organization/account foundation and privileged account bootstrap
- DEV / UAT / PROD account topology
- domain analytics databases and stable structural schemas
- domain/platform RBAC and database-role design
- domain workload warehouses and cost-control foundations
- workload identities / OIDC integrations
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
│   └── rbac/
└── stacks/
    ├── organization/
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

`organization/` alone uses ORGADMIN and manages DEV/UAT/PROD account resources with `prevent_destroy`. Routine account roots use lower account-level authority and will move to WIF/OIDC.

Database boundary is environment × domain, for example `DEV_HEALTH`, `CI_HEALTH`, `UAT_TRANSPORT`, and `PROD_TRANSPORT`. Physical source systems do not each receive a database merely for cost attribution.

## Domain access and compute

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

This gives Health, Transport, and future domains independent access and compute/cost boundaries without creating database-per-source.

## Current phase

**Phase 1 — Platform Foundation is in progress.**

Completed in source: version pinning, organization bootstrap root, three-account environment metadata, domain database/schema modules, workload warehouse guardrails, structural `PLATFORM_CONTROL`, domain GUEST/READER/DEVELOPER/ADMIN RBAC, DEV/UAT/PROD roots, and validation-only GitHub Actions CI.

Still pending before Phase 1 exit: successful Terraform execution/lock files, remote state, WIF/OIDC machine identities, controlled organization bootstrap/import, reviewed DEV plan/apply, Snowflake-side verification, personal/PR schema lifecycle, and cost-control hardening.

Kafka, Snowpipe Streaming, Openflow and broad dbt modelling remain intentionally deferred.
