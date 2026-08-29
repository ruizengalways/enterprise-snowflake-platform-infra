# Snowflake Account and Environment Topology

## Status

Phase 1 source/static-CI baseline. The platform targets three Snowflake accounts: DEV, UAT and PROD. Organization bootstrap, per-account Terraform identities, per-environment project deployment identities, DEV PR-CI identities, selectable Azure Blob/S3 state profiles and routine account roots are implemented in source. Real infrastructure bootstrap/plan/apply remains pending.

## Organization topology

```text
Snowflake Organization
├── DEV account
│   ├── DEV_HEALTH
│   ├── CI_HEALTH
│   ├── DEV_TRANSPORT
│   ├── CI_TRANSPORT
│   └── PLATFORM_CONTROL
├── UAT account
│   ├── UAT_HEALTH
│   ├── UAT_TRANSPORT
│   └── PLATFORM_CONTROL
└── PROD account
    ├── PROD_HEALTH
    ├── PROD_TRANSPORT
    └── PLATFORM_CONTROL
```

Account isolation is the environment/security lifecycle boundary. Database isolation is environment × governed domain/data product. Warehouse isolation is domain × workload compute/cost.

CI is not a fourth account. PR CI stays in DEV with separate `CI_<DOMAIN>` databases and `WH_<DOMAIN>_CI` warehouses.

## Bootstrap and lifecycle layers

### Organization bootstrap

```text
terraform/stacks/organization/
```

This is the only root using ORGADMIN. It creates/imports DEV/UAT/PROD account resources from `config/organization.yml`. Account lifecycle has destructive-change protection and must be reviewed explicitly.

### Platform Terraform identity bootstrap

```text
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
```

Create:

```text
DEV   SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
UAT   SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
PROD  SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Identity bootstrap may activate ACCOUNTADMIN; routine platform Terraform does not.

### Routine platform state

```text
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

These activate only their environment-specific `AR_TERRAFORM_<ENV>` role. Initial routine account privileges are:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Static Terraform validation cannot prove these privileges are sufficient in a live account. The first DEV plan/apply is the privilege-verification gate.

### Project workload identity bootstrap

```text
terraform/stacks/project-identity/dev/
terraform/stacks/project-identity/uat/
terraform/stacks/project-identity/prod/
```

These run only after the matching platform state has created the target machine roles.

DEV creates:

```text
SU_GITHUB_<DOMAIN>_CI     -> AR_<DOMAIN>_CI
SU_GITHUB_<DOMAIN>_DEPLOY -> AR_<DOMAIN>_DEPLOY
```

UAT/PROD create:

```text
SU_GITHUB_<DOMAIN>_DEPLOY -> AR_<DOMAIN>_DEPLOY
```

The project identity roots own service-user WIF trust + assignment only; role capabilities remain owned by platform RBAC Terraform.

## Terraform state topology

There are ten independent lifecycle states:

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

Per-environment dependency:

```text
identity/<env>
  -> platform/<env>
      -> project-identity/<env>
```

Remote state is backend-selectable:

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

A deployment chooses one authoritative writable state backend. GitHub OIDC access to the state backend is independent from GitHub OIDC/Snowflake WIF used for Snowflake authentication.

## Domain access model

Each domain has an independent human role hierarchy:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

`GUEST` is authenticated published-data read-only access and initially sees only `MARTS` and `SEMANTIC`. `READER` can inspect all stable layers. DEV `DEVELOPER` receives WRITE + transform compute. UAT/PROD human roles receive no permanent transform warehouse grant in the baseline.

Routine stable delivery uses the separate machine role:

```text
AR_<DOMAIN>_DEPLOY
```

Emergency human UAT/PROD transform execution is JIT/break-glass through enterprise identity governance.

## DEV account

Stable databases:

```text
DEV_HEALTH
DEV_TRANSPORT
```

CI databases:

```text
CI_HEALTH
CI_TRANSPORT
```

Stable schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Personal schemas are created outside Terraform using the convention:

```text
<DEVELOPER>_<LAYER>
```

PR schemas are also outside long-lived Terraform state:

```text
PR_<NUMBER>_<LAYER>
```

DEV warehouses:

```text
WH_HEALTH_QUERY
WH_HEALTH_TRANSFORM
WH_HEALTH_CI
WH_TRANSPORT_QUERY
WH_TRANSPORT_TRANSFORM
WH_TRANSPORT_CI
WH_PLATFORM_OPS
```

Access intent:

```text
GUEST/READER          -> QUERY
DEV DEVELOPER         -> TRANSFORM
AR_<DOMAIN>_CI        -> CI
AR_<DOMAIN>_DEPLOY    -> TRANSFORM
AR_PLATFORM_ENGINEER  -> PLATFORM_OPS
```

## UAT account

Databases:

```text
UAT_HEALTH
UAT_TRANSPORT
PLATFORM_CONTROL
```

Warehouses:

```text
WH_HEALTH_QUERY
WH_HEALTH_TRANSFORM
WH_TRANSPORT_QUERY
WH_TRANSPORT_TRANSFORM
WH_PLATFORM_OPS
```

UAT exists as a separate production-like account so account-scoped RBAC, workload identity, integrations and operations can be proven before PROD.

Human developers remain read-only by default. Routine transform delivery is machine-only through `AR_<DOMAIN>_DEPLOY`; no permanent human ADMIN transform grant is part of the baseline.

## PROD account

Databases:

```text
PROD_HEALTH
PROD_TRANSPORT
PLATFORM_CONTROL
```

Warehouses:

```text
WH_HEALTH_QUERY
WH_HEALTH_TRANSFORM
WH_TRANSPORT_QUERY
WH_TRANSPORT_TRANSFORM
WH_PLATFORM_OPS
```

Human developers remain read-only by default. Stable project deployment uses the protected project GitHub Environment `prod` and `SU_GITHUB_<DOMAIN>_DEPLOY -> AR_<DOMAIN>_DEPLOY`.

## Database boundary and many physical sources

A governed domain may ingest many MSSQL, MySQL, API, file or streaming sources without creating one database per source.

Example:

```text
PROD_HEALTH
├── RAW_EHR_MSSQL       # only when source onboarding creates it
├── RAW_BOOKING_MYSQL   # later
├── RAW_INSURANCE_API   # later
├── STAGING
├── INTERMEDIATE
├── CANONICAL
├── MARTS
└── SEMANTIC
```

The domain database is the ownership/storage/recovery boundary. Source-level cost attribution additionally uses query tags, warehouses and Snowflake usage/storage histories.

## `PLATFORM_CONTROL`

Every account owns an independent `PLATFORM_CONTROL` database with structural schemas:

```text
DEPLOYMENT
QUALITY
OBSERVABILITY
OPERATIONS
```

Native operational SQL currently owns checkpoint/run/check-result tables and the checkpoint advancement procedure inside this Terraform-created structural boundary.

Account-local operational state avoids making DEV/UAT/PROD runtime availability depend on a central cross-account control database.

## Retention baseline

Analytics/control databases initially use one day of Time Travel retention for portability and cost control. Account deletion grace remains separately configured through the organization lifecycle.

## Ownership boundary

- organization bootstrap owns Snowflake account resources;
- identity roots own platform Terraform service users/WIF;
- routine platform roots own domain databases, stable schemas, warehouses, role models and structural `PLATFORM_CONTROL`;
- project-identity roots own project CI/deployment service-user WIF bindings;
- framework/project workflows own ephemeral PR schema lifecycle and project delivery execution;
- dbt/project code owns transformation relations created inside its granted boundary;
- employee lifecycle belongs to enterprise IdP/SCIM.

## Live execution gate

```text
1. provision/select one authoritative remote-state backend
2. bootstrap/import Snowflake accounts
3. bootstrap identity/dev
4. reviewed platform/dev plan/apply
5. verify DEV databases/schemas/RBAC/warehouses/PLATFORM_CONTROL
6. bootstrap project-identity/dev
7. configure Health/Transport GitHub Environments ci + dev
8. prove real PR workspace WIF create/drop
9. prove immutable main-history DEV deployment
10. execute live SCD2 behavioral oracle
11. progress UAT with the same lifecycle order
12. progress protected PROD
```

See `TERRAFORM_STATE_AND_IDENTITY.md`, `RBAC_MODEL.md`, ADR-018, ADR-020, ADR-024 and ADR-034.
