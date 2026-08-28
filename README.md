# Enterprise Snowflake Platform Infrastructure

Central platform-engineering repository for the Enterprise Snowflake reference platform.

## Canonical architecture

The long-term project memory and authoritative architecture document is:

- [`docs/PROJECT_BLUEPRINT.md`](docs/PROJECT_BLUEPRINT.md)

The detailed target directory layout across all five repositories is:

- [`docs/architecture/REPOSITORY_LAYOUT.md`](docs/architecture/REPOSITORY_LAYOUT.md)

Snowflake naming rules are in:

- [`docs/standards/NAMING_CONVENTIONS.md`](docs/standards/NAMING_CONVENTIONS.md)

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

## Current phase

Phase 0 is complete. Repository layout is planned before implementation. The next implementation step is the smallest useful Phase 1 NONPROD Terraform foundation; Kafka, Snowpipe Streaming, Openflow and broad dbt modelling remain intentionally deferred.