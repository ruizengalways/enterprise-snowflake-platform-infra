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
    ├── {dev,uat,prod}/
    └── project-identity/{dev,uat,prod}/
```

Every root commits `.terraform.lock.hcl`; static CI uses read-only lock mode.

## Versions

```text
Terraform CLI:       1.16.0
Snowflake provider:  2.19.0
```

## Lifecycle order

Per environment:

```text
identity/<env>
  -> platform/<env>
      -> project-identity/<env>
```

Organization bootstrap/import happens before environment rollout and is the only ORGADMIN lifecycle.

`identity/<env>` bootstraps:

```text
SU_GITHUB_TERRAFORM_<ENV> -> AR_TERRAFORM_<ENV>
```

Routine `dev/uat/prod` activates only `AR_TERRAFORM_<ENV>`.

`project-identity/<env>` runs after the platform root and binds project WIF service users to already-existing machine roles.

DEV:

```text
SU_GITHUB_<DOMAIN>_CI     -> AR_<DOMAIN>_CI
SU_GITHUB_<DOMAIN>_DEPLOY -> AR_<DOMAIN>_DEPLOY
```

UAT/PROD:

```text
SU_GITHUB_<DOMAIN>_DEPLOY -> AR_<DOMAIN>_DEPLOY
```

The generic `service-identity` module creates only SERVICE user/WIF + role assignment; it does not create/expand the role or grant account-level privileges.

## Routine Terraform privileges

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine Terraform does not activate ACCOUNTADMIN/SYSADMIN/SECURITYADMIN. Privileges are widened only after a live plan/apply demonstrates a specific gap.

## Domain infrastructure

```text
DEV_<DOMAIN> / UAT_<DOMAIN> / PROD_<DOMAIN>
CI_<DOMAIN>   # DEV account only

AR_<DOMAIN>_GUEST -> READER -> DEVELOPER -> ADMIN
DR_<DOMAIN>_ANALYTICS_GUEST -> READ -> WRITE -> OWNER

AR_<DOMAIN>_CI      # machine-only PR CI in DEV
AR_<DOMAIN>_DEPLOY  # machine-only stable delivery

WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI      # DEV only
```

Project metadata declares query/transform/CI warehouse keys, so grants are derived instead of hard-coded per Health/Transport.

## DEV workspace access

Human domain RBAC attaches only to `DEV_<DOMAIN>`.

DEV WRITE receives `CREATE SCHEMA` on `DEV_<DOMAIN>` for personal `<DEVELOPER>_<LAYER>` namespaces. This naming convention is not per-person security isolation.

PR CI is machine-only:

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
  -> WH_<DOMAIN>_CI
  -> EXECUTE TASK
```

Human GUEST/READER/DEVELOPER/ADMIN roles do not attach to CI databases.

## Stable project deployment

```text
AR_<DOMAIN>_DEPLOY
  -> DR_<DOMAIN>_ANALYTICS_WRITE
  -> WH_<DOMAIN>_TRANSFORM
  -> CREATE STREAM/TASK/DYNAMIC TABLE
  -> EXECUTE TASK
```

This role is outside the human hierarchy. UAT/PROD human roles receive no permanent transform warehouse grant in the baseline; emergency execution is JIT/break-glass through enterprise identity governance.

## Remote state

Runtime selects:

```text
azurerm -> Azure Blob
s3      -> Amazon S3
```

through `terraform/scripts/select-backend.sh`, which materializes ignored `backend.generated.tf`.

There are ten state objects:

```text
organization
identity/dev
identity/uat
identity/prod
platform/dev
platform/uat
platform/prod
project-identity/dev
project-identity/uat
project-identity/prod
```

One backend is authoritative for a deployment. OneDrive/SharePoint is not live Terraform state.

## Static CI

Current matrix validates:

```text
terraform fmt + backend selector syntax
organization
identity/dev
identity/uat
identity/prod
dev
uat
prod
project-identity/dev
project-identity/uat
project-identity/prod
backend azurerm
backend s3
```

Static validation proves HCL/provider-schema correctness, not live Snowflake authorization.

## Live progression

```text
remote state
-> organization bootstrap/import
-> identity/dev
-> platform/dev reviewed plan/apply + verification
-> project-identity/dev
-> real PR workspace WIF test
-> real immutable DEV project deployment test
-> live SCD2 behavior test
-> UAT lifecycle
-> protected PROD lifecycle
```

`terraform-plan-dev.yml` remains manual-only and plan-only. No automated Terraform apply exists yet.

## Employee identity

Terraform defines roles/privileges. Employee joins/leaves and temporary break-glass access belong to enterprise IdP/SCIM/identity governance, not Terraform user records.

See `docs/standards/TERRAFORM_STANDARDS.md`, `docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md` and ADR-034.
