# Snowflake Naming Conventions

## Purpose

Define stable naming rules for the Enterprise Snowflake Platform. Physical environment names are configuration-driven; model SQL must not hard-code environment-specific database names.

## General conventions

- Snowflake objects: uppercase `SNAKE_CASE`.
- Git repositories and normal source files: lowercase kebab-case unless an ecosystem convention requires otherwise.
- Names describe capability, workload or ownership—not employee seniority.
- Avoid technology-specific names in downstream business objects unless the technology itself is the object's purpose.
- Environment-specific names are resolved from configuration.
- Any namespace shared by multiple project repositories must include a project discriminator where collisions are possible.

## Accounts and databases

Architectural accounts:

- `NONPROD`
- `PROD`

Analytics databases:

- `ANALYTICS_DEV`
- `ANALYTICS_CI`
- `ANALYTICS_UAT`
- `ANALYTICS_PROD`

Central control database:

- `PLATFORM_CONTROL`

## Schemas

Because analytics databases are shared by multiple project repositories, stable project schemas are project-qualified:

```text
<PROJECT>_<LAYER>
```

Approved initial layers:

- `STAGING`
- `INTERMEDIATE`
- `CANONICAL` when a distinct canonical layer is justified
- `MARTS`
- `SEMANTIC`

Examples:

- `HEALTH_STAGING`
- `HEALTH_INTERMEDIATE`
- `HEALTH_CANONICAL`
- `HEALTH_MARTS`
- `HEALTH_SEMANTIC`
- `TRANSPORT_STAGING`
- `TRANSPORT_MARTS`

Personal DEV schemas:

```text
<DEVELOPER>_<PROJECT>_<LAYER>
```

Examples:

- `ALICE_HEALTH_STAGING`
- `ALICE_HEALTH_INTERMEDIATE`
- `BOB_TRANSPORT_MARTS`

Ephemeral PR CI schemas:

```text
<PROJECT>_PR_<NUMBER>_<LAYER>
```

Examples:

- `HEALTH_PR_123_STAGING`
- `HEALTH_PR_123_MARTS`
- `TRANSPORT_PR_123_STAGING`

PR numbers are repository-local, so project qualification is mandatory. See ADR-016.

## Account roles

Pattern:

```text
AR_<SCOPE>_<CAPABILITY>
```

Platform examples:

- `AR_PLATFORM_READER`
- `AR_PLATFORM_ENGINEER`
- `AR_PLATFORM_ADMIN`

Project examples:

- `AR_HEALTH_READER`
- `AR_HEALTH_DEVELOPER`
- `AR_HEALTH_ADMIN`
- `AR_TRANSPORT_READER`
- `AR_TRANSPORT_DEVELOPER`
- `AR_TRANSPORT_ADMIN`

Do not use role names such as `JUNIOR`, `SENIOR`, `LEVEL1`, or `LEVEL2`.

## Database roles

Pattern:

```text
DR_<PROJECT>_ANALYTICS_<ACCESS>
```

Approved initial access suffixes:

- `READ`
- `WRITE`
- `OWNER`

Examples:

- `DR_HEALTH_ANALYTICS_READ`
- `DR_HEALTH_ANALYTICS_WRITE`
- `DR_HEALTH_ANALYTICS_OWNER`

Database-role names may repeat across different analytics databases because the database itself is part of the database-role identifier.

## Warehouses

Pattern:

```text
WH_<SCOPE>_<WORKLOAD>
```

For project workloads, `<SCOPE>` is normally the project code because this gives useful cost and workload isolation without multiplying warehouses unnecessarily.

NONPROD examples:

- `WH_HEALTH_DEV`
- `WH_HEALTH_CI`
- `WH_HEALTH_UAT`
- `WH_TRANSPORT_DEV`
- `WH_TRANSPORT_CI`
- `WH_TRANSPORT_UAT`
- `WH_PLATFORM_OPS`

PROD examples:

- `WH_HEALTH_TRANSFORM`
- `WH_HEALTH_QUERY`
- `WH_TRANSPORT_TRANSFORM`
- `WH_TRANSPORT_QUERY`
- `WH_PLATFORM_OPS`

Do not add separate warehouses unless workload isolation, security, performance, scheduling, or cost attribution justifies them.

## Platform control schemas

- `PLATFORM_CONTROL.DEPLOYMENT`
- `PLATFORM_CONTROL.QUALITY`
- `PLATFORM_CONTROL.OBSERVABILITY`
- `PLATFORM_CONTROL.OPERATIONS`

Initial planned tables:

```text
DEPLOYMENT.RELEASE_HISTORY
DEPLOYMENT.DEPLOYMENT_RUNS
DEPLOYMENT.ROLLBACK_HISTORY

QUALITY.TEST_RUNS
QUALITY.TEST_RESULTS
QUALITY.RECONCILIATION_RESULTS
QUALITY.DATA_INCIDENTS

OBSERVABILITY.DATASET_HEALTH
OBSERVABILITY.FRESHNESS_STATUS
OBSERVABILITY.PIPELINE_HEALTH
OBSERVABILITY.COST_STATUS

OPERATIONS.PIPELINE_RUNS
OPERATIONS.INCIDENTS
OPERATIONS.RECOVERY_RUNS
OPERATIONS.BACKFILL_RUNS
```

## Dataset and model names

Dataset identifiers in metadata use lowercase `snake_case` unless a source contract requires otherwise.

Prefer dbt model names that communicate layer and business meaning through directory/package context rather than redundant environment names. Never suffix models with `_DEV`, `_UAT` or `_PROD`.

## Load strategy identifiers

Approved identifiers:

```text
full_refresh
append_only
incremental_merge
scd2_snapshot
scd2_merge
scd2_stream_task
```

## Repositories

Canonical repository names:

- `enterprise-snowflake-platform-infra`
- `enterprise-snowflake-data-project-framework`
- `enterprise-snowflake-demo-source-systems`
- `enterprise-snowflake-health-analytics`
- `enterprise-snowflake-transport-analytics`

Future project repositories should normally follow:

```text
enterprise-snowflake-<project>-analytics
```

Example: `enterprise-snowflake-finance-analytics`.
