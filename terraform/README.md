# Terraform Platform Foundation

Terraform owns selected stable Snowflake platform infrastructure and machine-identity boundaries.

## Layout

```text
terraform/
├── backend-profiles/{azurerm,s3}/
├── scripts/select-backend.sh
├── modules/
│   ├── analytics-environment/
│   ├── warehouse/
│   ├── platform-control/
│   ├── rbac/
│   ├── workspace-access/
│   ├── workload-identity/
│   └── service-identity/
└── stacks/
    ├── organization/
    ├── identity/{dev,uat,prod}/
    ├── dev/
    ├── project-identity/dev/
    ├── uat/
    └── prod/
```

Every root commits `.terraform.lock.hcl`; CI uses `-lockfile=readonly`.

## Versions

```text
Terraform CLI:       1.16.0
Snowflake provider:  2.19.0
```

## Lifecycle order

```text
organization
-> identity/dev
-> platform/dev
-> project-identity/dev
-> UAT
-> PROD
```

`organization/` alone uses ORGADMIN.

`identity/<env>` bootstraps:

```text
SU_GITHUB_TERRAFORM_<ENV> -> AR_TERRAFORM_<ENV>
```

Routine `dev/uat/prod` activates only `AR_TERRAFORM_<ENV>`.

`project-identity/dev` runs after `platform/dev` and binds project WIF service users to existing machine CI roles:

```text
SU_GITHUB_HEALTH_CI    -> AR_HEALTH_CI
SU_GITHUB_TRANSPORT_CI -> AR_TRANSPORT_CI
```

The generic `service-identity` module creates only SERVICE user/WIF + role assignment; it does not create/expand the role or grant account-level privileges.

## Routine Terraform privileges

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine Terraform does not use ACCOUNTADMIN/SYSADMIN/SECURITYADMIN.

## Domain infrastructure

```text
DEV_<DOMAIN> / UAT_<DOMAIN> / PROD_<DOMAIN>
CI_<DOMAIN>   # DEV account only

AR_<DOMAIN>_GUEST -> READER -> DEVELOPER -> ADMIN
DR_<DOMAIN>_ANALYTICS_GUEST -> READ -> WRITE -> OWNER

WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI
```

Project metadata declares query/transform/CI warehouse keys, so grants are derived instead of hard-coded per Health/Transport.

## DEV workspace access

Human domain RBAC attaches only to `DEV_<DOMAIN>`.

DEV WRITE receives:

```text
CREATE SCHEMA on DEV_<DOMAIN>
```

for personal `<DEVELOPER>_<LAYER>` namespaces. This naming convention is not per-person security isolation.

PR CI is machine-only:

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> USAGE + CREATE SCHEMA
  -> WH_<DOMAIN>_CI
```

Human GUEST/READER/DEVELOPER/ADMIN roles do not attach to CI databases.

## Project CI identity boundary

DEV metadata contains only shared non-secret identity convention inputs (`github_owner`, environment `ci`, OIDC issuer) plus each project's existing code/repository.

Terraform derives:

```text
service user: SU_GITHUB_<DOMAIN>_CI
role:         AR_<DOMAIN>_CI
subject:      repo:<owner>/<project-repo>:environment:ci
```

The DEV account-scoped Snowflake OIDC audience remains an external bootstrap input.

See ADR-027.

## Remote state

Runtime selects:

```text
azurerm -> Azure Blob
s3      -> Amazon S3
```

via `terraform/scripts/select-backend.sh`, which materialises ignored `backend.generated.tf`.

There are eight state objects:

```text
organization
identity/dev
identity/uat
identity/prod
platform/dev
project-identity/dev
platform/uat
platform/prod
```

OneDrive/SharePoint is not live Terraform state.

## Static CI

Current matrix validates:

```text
terraform fmt + backend selector syntax
organization
identity/dev
identity/uat
identity/prod
dev
project-identity/dev
uat
prod
backend azurerm
backend s3
```

The project-identity root has passed Snowflake provider 2.19.0 init/validate in CI.

Static validation does not prove live Snowflake authorization.

## DEV remote plan

`terraform-plan-dev.yml` remains manual-only and plan-only. No automated apply exists yet.

Live progression must be:

```text
remote state
-> identity/dev
-> platform/dev reviewed plan/apply + verification
-> project-identity/dev
-> real project PR workspace test
```

## Employee identity

Terraform defines roles/privileges. Employee joins/leaves belong to enterprise IdP/SCIM, not Terraform user records.
