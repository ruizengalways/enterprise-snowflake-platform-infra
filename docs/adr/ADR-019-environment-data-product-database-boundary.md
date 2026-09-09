# ADR-019 — Environment × data-product database boundary and Medallion schemas

- **Status:** Accepted
- **Date:** 2026-08-28
- **Amended:** 2026-09-04
- **Supersedes:** ADR-016

## Context

The platform may ingest many physical source systems (MSSQL, MySQL, APIs, files, streams) for a smaller number of owned data products/domains. Creating a database per source would multiply lifecycle/RBAC objects and tie downstream architecture to source technology. Conversely, putting every data product into one environment-wide database weakens ownership, storage attribution, recovery and lifecycle boundaries.

The schema model must also stay understandable to engineers and architecture reviewers. Snowflake workloads are commonly explained with Bronze/Silver/Gold Medallion terminology, while this platform additionally needs explicit staging, intermediate, canonical and semantic responsibilities.

A normal new source should not require a platform Terraform change merely to obtain another RAW namespace.

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

Stable domain databases use one Medallion-aligned schema contract:

```text
BRONZE
SILVER_STAGING
SILVER_INTERMEDIATE
SILVER_CANONICAL
GOLD_MARTS
GOLD_SEMANTIC
DQ
```

Responsibilities are:

- `BRONZE`: source-preserving landed/captured data. Source identity remains explicit in Git metadata and object naming, for example `EHR_MSSQL__PATIENT` or `FLEET_MSSQL__VEHICLE_STATUS`.
- `SILVER_STAGING`: source-oriented cleanup, typing, renaming and deterministic deduplication.
- `SILVER_INTERMEDIATE`: non-consumer intermediate joins and reusable transformation steps.
- `SILVER_CANONICAL`: governed, conformed domain entities and standard history representations such as SCD2.
- `GOLD_MARTS`: analytics-ready business marts.
- `GOLD_SEMANTIC`: stable semantic/consumer-facing objects.
- `DQ`: domain data-quality/reconciliation outputs that are cross-cutting rather than a Medallion stage.

Only `GOLD_MARTS` and `GOLD_SEMANTIC` are published to the baseline domain guest role.

### Source-specific schema exceptions

An ordinary source does **not** create `BRONZE_<SOURCE>` through Terraform. Multiple sources coexist in `BRONZE` and are separated by dataset/source metadata, object naming, ownership contracts and query tags.

A separate source-specific schema is an explicit governance exception when there is a real security, retention, replication/share, legal or lifecycle boundary. It is not created merely because the connector technology differs.

This keeps source onboarding self-service at the domain repository layer while preserving a platform-owned stable database/schema boundary.

### CI and personal workspaces

CI databases remain separate from stable DEV databases. PR schemas are created and removed by project delivery workflows rather than Terraform state. Framework workspace naming mirrors the Medallion layer names, for example:

```text
PR_123_SILVER_STAGING
PR_123_SILVER_CANONICAL
PR_123_GOLD_MARTS
```

Personal DEV workspaces use the same layer suffixes when enabled.

## Configuration and control-plane consequence

Dataset behavior is not encoded in database/schema names. Capture and target/history behavior remain per-dataset Git metadata, for example watermark + SCD1, full-change + SCD2, cursor + append, or full-refresh + replace.

`PLATFORM_CONTROL` is shared platform state and is not part of Bronze/Silver/Gold. It contains stable control schemas including:

```text
CONFIG
OPERATIONS
QUALITY
OBSERVABILITY
DEPLOYMENT
```

Git remains the configuration source of truth. `PLATFORM_CONTROL.CONFIG.DATASET_CONFIG_SNAPSHOT` stores immutable deployment-time audit snapshots of validated dataset metadata; project roles do not mutate that base table directly. Operational progress remains separately stored in `PIPELINE_RUN`, `PIPELINE_CHECKPOINT`, `PIPELINE_BOOTSTRAP` and `PIPELINE_CHECK_RESULT`.

## Cost attribution

Database boundaries provide project/domain storage attribution and a clean unit for lifecycle/recovery. They are not the only cost-allocation mechanism.

Compute/serverless attribution additionally uses:

- project/workload warehouses;
- query tags carrying project/source/pipeline/dataset metadata;
- Snowflake usage history for warehouse/query/serverless services;
- table/schema storage metrics when source-level storage allocation is required.

Therefore 20 physical sources do not imply 20 databases or 20 Terraform-owned Bronze schemas.

## RBAC consequence

Each analytics database maps to exactly one owning project. Terraform must not create a Cartesian product of every project role in every database. The RBAC module consumes an explicit `database_projects` mapping and creates only the owning project's database-role hierarchy.

Terraform owns the stable schemas. Domain developers/deployment identities create normal data objects inside granted schemas but do not need `CREATE SCHEMA` for routine source onboarding.

## Consequences

- Data-product ownership is visible in fully-qualified object names.
- Architecture can be explained directly as Bronze → Silver → Gold without losing staging/canonical/semantic detail.
- Source technology changes do not force database redesign.
- Adding an ordinary source does not require platform Terraform changes.
- Source-specific isolation remains available when justified by governance rather than connector type.
- Git-owned per-dataset strategy metadata stays independent from physical database layout.
- Shared runtime/config control state remains outside the domain data plane.
