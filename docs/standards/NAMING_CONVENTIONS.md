# Snowflake Naming Conventions

## Purpose

Define stable naming rules for the Enterprise Snowflake Platform. Physical targets are configuration-driven; dbt model SQL must not hard-code environment-specific database names.

## General conventions

- Snowflake objects: uppercase `SNAKE_CASE`.
- Git repositories and normal source files: lowercase kebab-case unless an ecosystem convention requires otherwise.
- Names describe environment, ownership, capability or workload—not employee seniority.
- Do not encode source technology into downstream business objects unless the technology/source boundary is itself the object's purpose.
- Environment/account targets are resolved from configuration.

## Accounts

Architectural Snowflake accounts:

```text
DEV
UAT
PROD
```

DEV also hosts ephemeral PR CI. CI is isolated by database/schema/warehouse and later a dedicated workload identity; it is not a fourth Snowflake account.

## Analytics databases

Pattern:

```text
<ENVIRONMENT>_<PROJECT>
```

Current examples:

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

A database represents environment × data-product ownership. Do not create database-per-source merely because a project ingests many MSSQL/MySQL/API/file sources. See ADR-019.

Central control database in every account:

```text
PLATFORM_CONTROL
```

## Schemas

Because an analytics database is already project-scoped, stable transformation schemas use simple layer names:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

`CANONICAL` is used only when a distinct canonical layer is justified.

RAW schemas may identify source purpose when needed, for example:

```text
RAW_EHR_MSSQL
RAW_BOOKING_MYSQL
RAW_INSURANCE_API
```

Do not pre-create speculative RAW source schemas in the platform foundation; they are added through project/source onboarding metadata when a real source exists.

Personal DEV schemas inside a project DEV database:

```text
<DEVELOPER>_<LAYER>
```

Examples inside `DEV_HEALTH`:

```text
ALICE_STAGING
ALICE_INTERMEDIATE
ALICE_MARTS
```

Ephemeral PR schemas inside a project CI database:

```text
PR_<NUMBER>_<LAYER>
```

Examples inside `CI_HEALTH`:

```text
PR_123_STAGING
PR_123_MARTS
```

Project qualification is unnecessary in these schema names because `CI_HEALTH` and `CI_TRANSPORT` are separate databases.

## Account roles

Pattern:

```text
AR_<SCOPE>_<CAPABILITY>
```

Platform roles:

```text
AR_PLATFORM_READER
AR_PLATFORM_ENGINEER
AR_PLATFORM_ADMIN
```

Project roles:

```text
AR_HEALTH_READER
AR_HEALTH_DEVELOPER
AR_HEALTH_ADMIN
AR_TRANSPORT_READER
AR_TRANSPORT_DEVELOPER
AR_TRANSPORT_ADMIN
```

Do not use names such as `JUNIOR`, `SENIOR`, `LEVEL1`, or `LEVEL2`.

## Database roles

Pattern:

```text
DR_<PROJECT>_ANALYTICS_<ACCESS>
```

Approved access suffixes:

```text
READ
WRITE
OWNER
```

Examples:

```text
DR_HEALTH_ANALYTICS_READ
DR_HEALTH_ANALYTICS_WRITE
DR_HEALTH_ANALYTICS_OWNER
```

Database-role names may repeat in `DEV_HEALTH`, `CI_HEALTH`, `UAT_HEALTH`, and `PROD_HEALTH` because the database is part of the database-role identifier. A project database only receives roles for its owning project.

## Warehouses

Pattern:

```text
WH_<SCOPE>_<WORKLOAD>
```

DEV account examples:

```text
WH_HEALTH_DEV
WH_HEALTH_CI
WH_TRANSPORT_DEV
WH_TRANSPORT_CI
WH_PLATFORM_OPS
```

UAT account examples:

```text
WH_HEALTH_UAT
WH_TRANSPORT_UAT
WH_PLATFORM_OPS
```

PROD examples:

```text
WH_HEALTH_TRANSFORM
WH_HEALTH_QUERY
WH_TRANSPORT_TRANSFORM
WH_TRANSPORT_QUERY
WH_PLATFORM_OPS
```

Do not add separate warehouses unless workload isolation, security, performance, scheduling, or cost attribution justifies them.

## Platform control schemas

```text
PLATFORM_CONTROL.DEPLOYMENT
PLATFORM_CONTROL.QUALITY
PLATFORM_CONTROL.OBSERVABILITY
PLATFORM_CONTROL.OPERATIONS
```

Initial planned runtime tables are introduced only when a real consumer exists, for example `QUALITY.RECONCILIATION_RESULTS` and deployment/recovery history.

## Dataset and model names

Dataset identifiers in metadata use lowercase `snake_case` unless a source contract requires otherwise.

Prefer dbt model names that communicate layer and business meaning through directory/package context. Never suffix models with `_DEV`, `_UAT` or `_PROD`.

## Load strategy identifiers

```text
full_refresh
append_only
incremental_merge
scd2_snapshot
scd2_merge
scd2_stream_task
```

## Repositories

Canonical repositories:

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

Future project repositories normally follow:

```text
enterprise-snowflake-<project>-analytics
```
