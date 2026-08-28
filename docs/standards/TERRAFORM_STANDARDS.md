# Terraform Standards

## Scope

These standards apply to `enterprise-snowflake-platform-infra`.

## Version policy

- Terraform CLI is pinned by `.terraform-version`.
- Snowflake provider is pinned exactly in each root stack.
- Current baseline: Terraform `1.16.0`, `snowflakedb/snowflake` provider `2.19.0`.
- Provider upgrades require migration-guide review and CI validation; do not use an unbounded `latest` constraint.
- `.terraform.lock.hcl` is committed for every root and CI uses `-lockfile=readonly`.

## Authentication

Never place passwords, private keys, OAuth tokens, PATs, or cloud access keys in Git.

Routine DEV/UAT/PROD roots expose lifecycle provider aliases:

```text
snowflake.objects
snowflake.security
```

Both aliases run under the environment's dedicated routine Terraform account role:

```text
DEV  -> AR_TERRAFORM_DEV
UAT  -> AR_TERRAFORM_UAT
PROD -> AR_TERRAFORM_PROD
```

They do **not** use `SYSADMIN` or `SECURITYADMIN` as the routine CI authority.

GitHub -> Snowflake authentication uses Workload Identity Federation with GitHub OIDC. The matching Snowflake service users are:

```text
SU_GITHUB_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD
```

`ACCOUNTADMIN` is permitted only in the separate identity bootstrap lifecycle. Organization account creation uses the separate organization bootstrap provider authority.

## Privileged bootstrap boundaries

Organization root:

```text
terraform/stacks/organization/
```

It owns DEV/UAT/PROD Snowflake account resources and protects them with `prevent_destroy`.

Identity roots:

```text
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
```

They own each environment's GitHub OIDC service user and routine Terraform role. Service users and machine roles use `prevent_destroy`.

Normal DEV/UAT/PROD roots never create Snowflake accounts or their own authentication identity.

## Routine Terraform role privileges

Initial account-level privileges are deliberately explicit:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Do not grant `ACCOUNTADMIN`, `SYSADMIN`, or `SECURITYADMIN` to routine GitHub Terraform users. Add another privilege only when an implemented Terraform-owned capability requires it.

`MANAGE GRANTS` is powerful; `AR_TERRAFORM_<ENV>` is therefore machine-only and is never a domain/human role.

## Remote state

Terraform state is never committed.

Reference backend: Amazon S3 with:

```hcl
terraform {
  backend "s3" {
    encrypt      = true
    use_lockfile = true
  }
}
```

Bucket and region are supplied as partial backend configuration. Do not use DynamoDB locking.

The state bucket is a one-time control-plane prerequisite and must have versioning, encryption, blocked public access, restrictive IAM and recovery/audit coverage.

State object boundaries:

```text
enterprise-snowflake-platform-infra/organization/terraform.tfstate
enterprise-snowflake-platform-infra/identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/identity/uat/terraform.tfstate
enterprise-snowflake-platform-infra/identity/prod/terraform.tfstate
enterprise-snowflake-platform-infra/platform/dev/terraform.tfstate
enterprise-snowflake-platform-infra/platform/uat/terraform.tfstate
enterprise-snowflake-platform-infra/platform/prod/terraform.tfstate
```

GitHub uses AWS OIDC to access state. Do not store AWS access keys in GitHub.

See ADR-022 and `docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`.

## Root stack pattern

Current roots:

```text
terraform/stacks/organization/
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

Routine account roots:

1. pin Terraform/provider versions and committed lock files;
2. use the environment-specific `AR_TERRAFORM_<ENV>` role;
3. read YAML from `config/environments/`;
4. compose reusable modules;
5. contain no credentials;
6. expose useful object-name outputs;
7. contain no domain business logic.

Identity roots are separate because routine automation must not own the state that can destroy its own authentication path.

## Module pattern

Initial modules:

- `analytics-environment` — one domain analytics database plus stable schemas;
- `warehouse` — standard warehouse guardrails;
- `platform-control` — account-local `PLATFORM_CONTROL` database/schemas;
- `rbac` — platform/domain account roles, domain database roles, guest/read/write access and warehouse grants;
- `workload-identity` — Snowflake service user + dedicated routine Terraform role + GitHub OIDC trust.

A database passed to RBAC has exactly one owning domain through `database_projects`. Do not recreate a domain × database Cartesian product.

Published consumer schemas are passed separately through `published_schemas_by_database`; they must be a subset of stable schemas and initially represent `MARTS` and `SEMANTIC`.

Do not create a module only to wrap a single line or hide genuine business differences.

## OIDC rules

GitHub Environments are named exactly:

```text
dev
uat
prod
```

Snowflake OIDC subjects are pinned to repository + environment, for example:

```text
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:dev
```

Use an account-scoped `SNOWFLAKE_OIDC_AUDIENCE`; do not use the shared `snowflakecomputing.com` audience for these Terraform identities.

The Snowflake provider's WIF-management experiment `USER_ENABLE_DEFAULT_WORKLOAD_IDENTITY` is enabled only in identity bootstrap roots. Routine WIF authentication itself does not require that experiment in normal roots.

See ADR-023.

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

Configuration may describe database/domain mapping, stable schemas, published schemas, retention, warehouse sizing, timeouts and workload-identity names/subjects. Credentials are never configuration metadata.

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

Cost/resource monitors remain a later Phase 1 capability.

## Validation

Every Terraform change must pass:

```text
terraform fmt -check -recursive
terraform init -backend=false -input=false -lockfile=readonly
terraform validate
```

Current static CI matrix targets all seven roots.

Remote plan is deliberately separate from static CI. `terraform-plan-dev.yml` is manual-only and requires the real S3/AWS OIDC and Snowflake WIF configuration before it can execute.

No automated apply is enabled yet.
