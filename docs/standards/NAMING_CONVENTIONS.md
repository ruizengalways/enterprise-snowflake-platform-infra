# Snowflake Naming Conventions

## Purpose

Define stable naming rules for the Enterprise Snowflake Platform. Physical targets are configuration-driven; dbt/model SQL must not hard-code environment-specific database names.

## General conventions

- Snowflake objects: uppercase `SNAKE_CASE`.
- Git repositories and normal source files: lowercase kebab-case unless an ecosystem convention requires otherwise.
- Names describe environment, ownership, capability or workload—not employee seniority.
- Do not encode source technology into downstream business objects unless the source boundary is itself the object's purpose.
- `PROJECT` / `DOMAIN` means the governed data-product code, e.g. `HEALTH` or `TRANSPORT`.
- The Snowflake account already identifies DEV/UAT/PROD for most project-owned objects, so do not repeat environment tokens where account scope is sufficient.

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

A database represents environment/workspace class × domain, not one physical source.

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

Developer tokens are normalized by the shared framework to uppercase unquoted-identifier-safe characters. This prefix is a workspace namespace, not a per-person security boundary.

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

Project PR CI in DEV:

```text
AR_<DOMAIN>_CI
```

Stable project deployment in each environment account:

```text
AR_<DOMAIN>_DEPLOY
```

Examples:

```text
AR_HEALTH_CI
AR_TRANSPORT_CI
AR_HEALTH_DEPLOY
AR_TRANSPORT_DEPLOY
```

Machine roles do not participate in the human domain capability hierarchy.

## Service users

Use explicit purpose-specific conventions rather than one universal token order.

Platform Terraform identities include the environment because the same repository manages multiple account lifecycles:

```text
SU_GITHUB_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD
```

Project PR CI identities exist only in the DEV account:

```text
SU_GITHUB_<DOMAIN>_CI
```

Stable project deployment identities exist separately in each Snowflake account, so the account supplies the environment boundary and the object name remains stable:

```text
SU_GITHUB_<DOMAIN>_DEPLOY
```

Examples:

```text
DEV account:  SU_GITHUB_HEALTH_DEPLOY
UAT account:  SU_GITHUB_HEALTH_DEPLOY
PROD account: SU_GITHUB_HEALTH_DEPLOY
```

These are different account-local objects with different GitHub Environment subjects/audiences. Do not encode human names into service-user identifiers.

## Stable database roles

Stable human/database-access role pattern:

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

It grants the CI machine role the database/schema-creation boundary needed for ephemeral PR workspaces.

## Warehouses

```text
WH_<DOMAIN>_<WORKLOAD>
```

Per-domain baseline:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV account only
```

Platform operations:

```text
WH_PLATFORM_OPS
```

Access intent:

```text
GUEST/READER       -> QUERY
DEV DEVELOPER      -> TRANSFORM
AR_<DOMAIN>_DEPLOY -> TRANSFORM
AR_<DOMAIN>_CI     -> CI (DEV only)
```

UAT/PROD human roles have no permanent TRANSFORM warehouse grant in the baseline. Emergency human execution is JIT/break-glass through enterprise identity governance.

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

Terraform owns the structural database/schema boundary. Native platform SQL owns operational tables/procedures inside those schemas when a real lifecycle exists.

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
