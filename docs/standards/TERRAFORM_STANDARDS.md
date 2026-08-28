# Terraform Standards

## Scope

These standards apply to `enterprise-snowflake-platform-infra`.

## Version policy

- Terraform CLI is pinned by `.terraform-version`.
- Snowflake provider is pinned exactly in each root stack.
- Current baseline: Terraform `1.16.0`, `snowflakedb/snowflake` provider `2.19.0`.
- Provider upgrades require migration-guide review and CI validation; do not use an unbounded `latest` constraint.
- `.terraform.lock.hcl` is committed after a successful connected `terraform init`.

## Authentication

Never place passwords, private keys, OAuth tokens, PATs, or account secrets in Git.

Routine account stacks use provider aliases for lifecycle roles while authentication remains external to source control:

```text
snowflake.sysadmin
snowflake.securityadmin
```

GitHub -> Snowflake Workload Identity Federation is the target machine-authentication mechanism.

`ACCOUNTADMIN` is not a routine Terraform execution role. `ORGADMIN` is only relevant to the separate organization/account bootstrap lifecycle.

## Account bootstrap boundary

Snowflake provider `2.19.0` has a stable `snowflake_account` resource, but account creation requires organization privilege and initial account-admin material. Therefore:

```text
organization bootstrap (ORGADMIN, narrowly controlled)
            ↓
        DEV / UAT / PROD accounts
            ↓
independent account Terraform stacks
```

Do not place account creation in `terraform/stacks/dev`, `uat`, or `prod`; those stacks must connect to an account that already exists.

## State

Terraform state is never committed.

Before shared apply, each account must have a durable remote-state boundary with locking/recovery:

```text
DEV state
UAT state
PROD state
```

Do not share one undifferentiated state file across the three accounts. Backend technology remains undecided until the hosting/security boundary is selected.

Until the backend ADR is accepted, CI may run `fmt`, `init -backend=false`, and `validate`; automated apply remains disabled.

## Root stack pattern

Deployable account roots:

```text
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

Each root stack:

1. pins Terraform/provider versions;
2. configures provider aliases;
3. reads its YAML from `config/environments/`;
4. composes reusable modules;
5. contains no credentials;
6. exposes useful object-name outputs;
7. contains no project business logic.

## Module pattern

Initial modules:

- `analytics-environment` — one project analytics database plus stable schemas;
- `warehouse` — standard warehouse guardrails;
- `platform-control` — account-local `PLATFORM_CONTROL` database/schemas;
- `rbac` — account roles, project database roles and grants.

A database passed to RBAC has exactly one owning project through `database_projects`. Do not recreate the old project × database Cartesian product.

Do not create a module only to wrap a single line or hide genuine business differences.

## Resource ownership

Terraform owns selected stable platform infrastructure/RBAC. It does not own dbt models, business transformations or routine data changes.

One Snowflake object has one authoritative owner.

## Naming and metadata

Object names come from environment/project configuration and follow `NAMING_CONVENTIONS.md`.

Database boundary:

```text
<ENVIRONMENT>_<PROJECT>
```

Examples: `DEV_HEALTH`, `CI_HEALTH`, `UAT_TRANSPORT`, `PROD_TRANSPORT`.

Configuration may describe database/project mapping, stable schemas, retention, warehouse sizing and timeout guardrails. Credentials are never configuration metadata.

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

Cost/resource monitors remain a later Phase 1 capability because their administrative boundary should not force routine Terraform to use `ACCOUNTADMIN`.

## Validation

Every Terraform change must pass for DEV, UAT and PROD:

```text
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

Plan/apply checks are added only after account authentication and remote state are established.
