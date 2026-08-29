# Snowflake Naming Conventions

## Purpose

Define stable naming rules for the Enterprise Snowflake Platform. Physical targets are configuration-driven; dbt/model SQL must not hard-code environment-specific database names.

## General conventions

- Snowflake objects: uppercase `SNAKE_CASE`.
- Git repositories and normal source files: lowercase kebab-case unless an ecosystem convention requires otherwise.
- Names describe environment, ownership, capability or workload—not employee seniority.
- Do not encode source technology into downstream business objects unless the source boundary is itself the object's purpose.
- `PROJECT` / `DOMAIN` means the governed data product code, e.g. `HEALTH` or `TRANSPORT`.

## Accounts

```text
DEV
UAT
PROD
```

CI is hosted in DEV; it is not a fourth Snowflake account.

## Analytics databases

```text
<ENVIRONMENT>_<DOMAIN>
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

A database represents environment × domain, not one physical source.

Every account also owns:

```text
PLATFORM_CONTROL
```

## Stable schemas

Inside stable domain databases:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Published schemas initially:

```text
MARTS
SEMANTIC
```

RAW source-purpose schemas are added only when a real source is onboarded, for example:

```text
RAW_EHR_MSSQL
RAW_INSURANCE_API
```

## Personal DEV schemas

Inside `DEV_<DOMAIN>`:

```text
<DEVELOPER>_<LAYER>
```

Examples:

```text
DEV_HEALTH.ALICE_SMITH_STAGING
DEV_HEALTH.ALICE_SMITH_MARTS
```

Developer tokens are normalised by the shared framework to uppercase unquoted-identifier-safe characters. This prefix is a workspace namespace, not a per-person security boundary.

## PR CI schemas

Inside `CI_<DOMAIN>`:

```text
PR_<NUMBER>_<LAYER>
```

Examples:

```text
CI_HEALTH.PR_123_STAGING
CI_HEALTH.PR_123_MARTS
```

PR schemas are transient/reproducible workspaces and are not long-lived Terraform resources.

## Human account roles

```text
AR_<DOMAIN>_GUEST
AR_<DOMAIN>_READER
AR_<DOMAIN>_DEVELOPER
AR_<DOMAIN>_ADMIN
```

Capability inheritance:

```text
GUEST -> READER -> DEVELOPER -> ADMIN
```

Examples:

```text
AR_HEALTH_GUEST
AR_HEALTH_DEVELOPER
AR_TRANSPORT_GUEST
AR_TRANSPORT_ADMIN
```

`GUEST` is authenticated published-data read access, not anonymous/public access.

Platform human roles:

```text
AR_PLATFORM_READER
AR_PLATFORM_ENGINEER
AR_PLATFORM_ADMIN
```

## Machine account roles

Platform Terraform:

```text
AR_TERRAFORM_DEV
AR_TERRAFORM_UAT
AR_TERRAFORM_PROD
```

PR CI machine capability in DEV:

```text
AR_<DOMAIN>_CI
```

Examples:

```text
AR_HEALTH_CI
AR_TRANSPORT_CI
```

Machine roles do not participate in the human domain capability hierarchy.

## Service users

General machine service-user pattern:

```text
SU_<SYSTEM>_<PURPOSE>_<ENVIRONMENT>
```

Current platform Terraform identities:

```text
SU_GITHUB_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD
```

Project CI/deployment service users will follow a similarly explicit purpose/domain convention when those workload identities are implemented. Do not encode human names into service-user identifiers.

## Stable database roles

Stable human database-role pattern:

```text
DR_<DOMAIN>_ANALYTICS_<ACCESS>
```

Approved access values:

```text
GUEST
READ
WRITE
OWNER
```

Example:

```text
DEV_HEALTH.DR_HEALTH_ANALYTICS_WRITE
```

Human stable database roles are not created in `CI_<DOMAIN>` databases.

## CI database role

Machine-only PR workspace role:

```text
CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
```

Examples:

```text
CI_HEALTH.DR_HEALTH_CI_WORKSPACE
CI_TRANSPORT.DR_TRANSPORT_CI_WORKSPACE
```

It grants database `USAGE` + `CREATE SCHEMA` to `AR_<DOMAIN>_CI`.

## Warehouses

```text
WH_<DOMAIN>_<WORKLOAD>
```

Per-domain baseline:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
```

Platform operations:

```text
WH_PLATFORM_OPS
```

Access intent:

```text
GUEST/READER       -> QUERY
DEV DEVELOPER      -> TRANSFORM
UAT/PROD ADMIN     -> TRANSFORM (transitional)
AR_<DOMAIN>_CI     -> CI
```

Environment project metadata identifies each domain's warehouse keys; root Terraform should not hard-code Health/Transport grant blocks.

## Query tags

`QUERY_TAG` is compact JSON rather than a Snowflake object identifier. Standard keys are lowercase:

```text
project
environment
workload
source
pipeline
dataset
run_id
git_sha
pr_number
operation
```

Required keys are `project`, `environment`, `workload`.

Example:

```json
{"dataset":"patient","environment":"ci","pr_number":123,"project":"health","workload":"pr_ci"}
```

Do not place personal, secret, regulated or business payload data in query tags.

## Platform control schemas

```text
PLATFORM_CONTROL.DEPLOYMENT
PLATFORM_CONTROL.QUALITY
PLATFORM_CONTROL.OBSERVABILITY
PLATFORM_CONTROL.OPERATIONS
```

Runtime tables/views are introduced only when a real consumer/lifecycle exists.

## Dataset/model names

Dataset metadata uses lowercase `snake_case` unless a source contract requires otherwise. Never suffix dbt models with `_DEV`, `_UAT` or `_PROD`.

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

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

Future project repositories normally follow:

```text
enterprise-snowflake-<domain>-analytics
```
