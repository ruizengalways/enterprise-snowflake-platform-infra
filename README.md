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

- Snowflake organization/account foundation and bootstrap architecture
- DEV / UAT / PROD account topology
- project/domain analytics databases and stable structural schemas
- central RBAC and database-role design
- warehouses and cost-control foundations
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
    ├── dev/
    ├── uat/
    └── prod/
```

Environment metadata:

```text
config/environments/dev.yml
config/environments/uat.yml
config/environments/prod.yml
```

Database boundary is environment × data product, for example `DEV_HEALTH`, `CI_HEALTH`, `UAT_TRANSPORT`, and `PROD_TRANSPORT`. Physical source systems do not each receive a database merely for cost attribution.

The code is credential-free in source control. Automated shared apply remains disabled until durable remote state and GitHub-to-Snowflake workload identity federation are implemented.

## Current phase

**Phase 1 — Platform Foundation is in progress.**

Completed in code: version pinning, three-account environment metadata, project database/schema modules, warehouse guardrails, structural `PLATFORM_CONTROL`, project-aware RBAC, DEV/UAT/PROD root stacks, and validation-only GitHub Actions CI.

Still pending before Phase 1 exit: provider lock files, remote state, workload identity federation, organization/account bootstrap execution, reviewed DEV plan/apply, Snowflake-side verification, personal/PR schema lifecycle and cost-control hardening.

Kafka, Snowpipe Streaming, Openflow and broad dbt modelling remain intentionally deferred.
