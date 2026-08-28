# ADR-019 — Environment × data-product database boundary

- **Status:** Accepted
- **Date:** 2026-08-28
- **Supersedes:** ADR-016

## Context

The platform may ingest many physical source systems (MSSQL, MySQL, APIs, files, streams) for a smaller number of owned data products/domains. Creating a database per source would multiply lifecycle/RBAC objects and tie downstream architecture to source technology. Conversely, putting every data product into one environment-wide database weakens ownership, storage attribution, recovery and lifecycle boundaries.

## Decision

Analytics databases are created per **environment × data product**, not per source system.

Pattern:

```text
<ENVIRONMENT>_<PROJECT>
```

Examples:

```text
DEV_HEALTH
CI_HEALTH
UAT_HEALTH
PROD_HEALTH

DEV_TRANSPORT
CI_TRANSPORT
UAT_TRANSPORT
PROD_TRANSPORT
```

Inside a project-specific database, stable transformation schemas use simple layer names:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

RAW storage may use source-purpose schemas such as `RAW_EHR_MSSQL` or `RAW_INSURANCE_API` when a project has enough sources to justify separate namespaces. Those source schemas are project metadata/onboarding concerns and are not pre-created speculatively in the Phase 1 core foundation.

Personal DEV schemas use:

```text
<DEVELOPER>_<LAYER>
```

Example: `ALICE_STAGING` inside `DEV_HEALTH`.

Ephemeral CI schemas use:

```text
PR_<NUMBER>_<LAYER>
```

Example: `PR_123_STAGING` inside `CI_HEALTH`. PR numbers cannot collide across projects because each project owns a different CI database.

## Cost attribution

Database boundaries provide project/domain storage attribution and a clean unit for lifecycle/recovery. They are not the only cost-allocation mechanism.

Compute/serverless attribution additionally uses:

- project/workload warehouses;
- query tags carrying project/source/pipeline/dataset metadata;
- Snowflake usage history for warehouse/query/serverless services;
- table/schema storage metrics when source-level storage allocation is required.

Therefore 20 physical sources do not imply 20 databases.

## RBAC consequence

Each analytics database maps to exactly one owning project. Terraform must not create a Cartesian product of every project role in every database. The RBAC module consumes an explicit `database_projects` mapping and creates only the owning project's database-role hierarchy.

## Consequences

- Data-product ownership is visible in fully-qualified object names.
- Storage/recovery lifecycle can be attributed and operated per project.
- Source technology changes do not force database redesign.
- Stable schema names become simpler because project scope already exists at database level.
- Onboarding a new data product creates environment databases through metadata/configuration; adding a new source normally does not.
