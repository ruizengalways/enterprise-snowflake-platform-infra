# Terraform Standards

## Scope

These standards apply to `enterprise-snowflake-platform-infra`.

## Version policy

- Terraform CLI is pinned by `.terraform-version`.
- Snowflake provider is pinned exactly in each root stack.
- Current baseline: Terraform `1.16.0`, `snowflakedb/snowflake` provider `2.19.0`.
- Provider upgrades require migration-guide review and CI validation; do not use an unbounded `latest` constraint.
- `.terraform.lock.hcl` is committed after a successful connected `terraform init` for each root.

## Authentication

Never place passwords, private keys, OAuth tokens, PATs, or account secrets in Git.

Routine account stacks use provider aliases:

```text
snowflake.sysadmin
snowflake.securityadmin
```

GitHub -> Snowflake Workload Identity Federation is the target routine machine-authentication mechanism.

`ACCOUNTADMIN` is not a routine Terraform execution role.

Organization bootstrap alone uses:

```text
snowflake.orgadmin
```

Its initial account-admin email and RSA public key are variables supplied outside source control. The private key is never committed.

## Organization bootstrap boundary

Provider `2.19.0` exposes stable `snowflake_account`. The isolated root is:

```text
terraform/stacks/organization/
```

It reads `config/organization.yml` and owns DEV/UAT/PROD account resources. Account resources use `prevent_destroy = true`.

Normal DEV/UAT/PROD roots never create accounts and never use ORGADMIN.

## State

Terraform state is never committed.

Shared execution requires four independent durable state boundaries with locking/recovery:

```text
organization state
DEV state
UAT state
PROD state
```

Do not share one undifferentiated state file across accounts or combine organization-level authority with routine account state.

Backend technology remains undecided until the hosting/security boundary is selected. Until the backend ADR is accepted, CI may run `fmt`, `init -backend=false`, and `validate`; automated apply remains disabled.

## Root stack pattern

Deployable roots:

```text
terraform/stacks/organization/
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

Organization root:

1. pins Terraform/provider versions;
2. uses only ORGADMIN provider authority;
3. reads `config/organization.yml`;
4. contains no routine database/RBAC/project logic;
5. protects account resources from ordinary destroy.

Account roots:

1. pin Terraform/provider versions;
2. configure SYSADMIN/SECURITYADMIN aliases;
3. read their YAML from `config/environments/`;
4. compose reusable modules;
5. contain no credentials;
6. expose useful object-name outputs;
7. contain no domain business logic.

## Module pattern

Initial modules:

- `analytics-environment` — one domain analytics database plus stable schemas;
- `warehouse` — standard warehouse guardrails;
- `platform-control` — account-local `PLATFORM_CONTROL` database/schemas;
- `rbac` — platform/domain account roles, domain database roles, guest/read/write access and warehouse grants.

A database passed to RBAC has exactly one owning domain through `database_projects`. Do not recreate a domain × database Cartesian product.

Published consumer schemas are passed separately through `published_schemas_by_database`; they must be a subset of the stable schemas and initially represent `MARTS` and `SEMANTIC`.

Do not create a module only to wrap a single line or hide genuine business differences.

## Resource ownership

Terraform owns selected stable platform infrastructure/RBAC. It does not own dbt models, business transformations or routine data changes.

One Snowflake object has one authoritative owner.

## Naming and metadata

Database pattern:

```text
<ENVIRONMENT>_<DOMAIN>
```

Examples: `DEV_HEALTH`, `CI_HEALTH`, `UAT_TRANSPORT`, `PROD_TRANSPORT`.

Domain role hierarchy:

```text
AR_<DOMAIN>_GUEST -> READER -> DEVELOPER -> ADMIN
```

Database-role hierarchy:

```text
DR_<DOMAIN>_ANALYTICS_GUEST -> READ -> WRITE -> OWNER
```

Warehouse pattern:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
```

Configuration may describe database/domain mapping, stable schemas, published schemas, retention, warehouse sizing and timeout guardrails. Credentials are never configuration metadata.

## Warehouse defaults

Baseline warehouses use conservative settings unless evidence requires otherwise:

- standard warehouse type;
- `XSMALL` initial size;
- auto-resume enabled;
- auto-suspend normally 60 seconds;
- initially suspended;
- explicit statement timeout;
- no query acceleration by default;
- no multi-cluster scaling without evidence.

Cost/resource monitors remain a later Phase 1 capability because their administrative boundary should not silently force routine Terraform to use `ACCOUNTADMIN`.

## Validation

Every Terraform change must pass for all roots:

```text
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

Current CI matrix targets:

```text
organization
dev
uat
prod
```

Plan/apply checks are added only after authentication and remote state are established.
