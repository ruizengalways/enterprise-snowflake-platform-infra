# Enterprise Snowflake Platform Infrastructure

Central platform-engineering repository for the Enterprise Snowflake reference platform.

## Canonical architecture

The long-term project memory and authoritative architecture document is:

- [`docs/PROJECT_BLUEPRINT.md`](docs/PROJECT_BLUEPRINT.md)

Supporting architecture:

- [`docs/architecture/REPOSITORY_LAYOUT.md`](docs/architecture/REPOSITORY_LAYOUT.md)
- [`docs/architecture/ACCOUNT_TOPOLOGY.md`](docs/architecture/ACCOUNT_TOPOLOGY.md)
- [`docs/architecture/RBAC_MODEL.md`](docs/architecture/RBAC_MODEL.md)
- [`docs/standards/NAMING_CONVENTIONS.md`](docs/standards/NAMING_CONVENTIONS.md)
- [`docs/standards/TERRAFORM_STANDARDS.md`](docs/standards/TERRAFORM_STANDARDS.md)

Architecture decisions are recorded under `docs/adr/`.

## This repository owns

- Snowflake organisation/account foundation
- NONPROD / PROD platform topology
- central RBAC and database-role design
- reusable Terraform project bootstrap infrastructure
- workload identities / OIDC and integrations
- shared governance
- central cost controls
- `PLATFORM_CONTROL` structural/operational foundation
- central observability and recovery architecture
- platform-level standards, ADRs and runbooks

## This repository does not own

- Health or Transport business transformations
- project-specific dbt models
- generic reusable dbt framework logic that belongs in `enterprise-snowflake-data-project-framework`
- source-system simulation
- Metric Guard

## Terraform foundation

Current Terraform code lives under [`terraform/`](terraform/):

```text
terraform/
├── modules/
│   ├── analytics-environment/
│   ├── warehouse/
│   ├── platform-control/
│   └── rbac/
└── stacks/
    ├── nonprod/
    └── prod/
```

Environment object metadata is in:

```text
config/environments/nonprod.yml
config/environments/prod.yml
```

The code is intentionally credential-free in source control. Automated shared apply remains disabled until durable remote Terraform state and GitHub-to-Snowflake workload identity federation are implemented.

## Current phase

**Phase 1 — Platform Foundation is in progress.**

Completed in code: Terraform/provider version pinning, NONPROD/PROD environment metadata, database/schema/warehouse modules, structural `PLATFORM_CONTROL`, capability/database RBAC, NONPROD/PROD root stacks, and validation-only GitHub Actions CI.

Still pending before Phase 1 exit: successful connected Terraform init/lock files, remote state, workload identity federation, reviewed NONPROD plan/apply, Snowflake-side verification, project/personal/PR schema bootstrap lifecycle, and cost-control hardening.

Kafka, Snowpipe Streaming, Openflow and broad dbt modelling remain intentionally deferred.
