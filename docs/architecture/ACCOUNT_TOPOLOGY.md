# Snowflake Account and Environment Topology

## Status

Phase 1 executable baseline. The platform targets three Snowflake accounts: DEV, UAT and PROD. Organization account bootstrap, per-account Terraform workload-identity bootstrap, S3 remote-state contracts, and routine account roots are implemented in source. Real infrastructure bootstrap/plan/apply remains gated on external account/state configuration.

## Organisation topology

```text
Snowflake Organization
│
├── DEV account
│   ├── DEV_HEALTH
│   ├── CI_HEALTH
│   ├── DEV_TRANSPORT
│   ├── CI_TRANSPORT
│   └── PLATFORM_CONTROL
│
├── UAT account
│   ├── UAT_HEALTH
│   ├── UAT_TRANSPORT
│   └── PLATFORM_CONTROL
│
└── PROD account
    ├── PROD_HEALTH
    ├── PROD_TRANSPORT
    └── PLATFORM_CONTROL
```

Account isolation is the lifecycle/security boundary. Database isolation is environment × data-product/domain ownership plus storage/recovery boundary. Warehouse isolation is domain × workload compute/cost boundary.

## Bootstrap layers

### Organization bootstrap

```text
terraform/stacks/organization/
```

is the only Terraform root using `ORGADMIN`. It manages DEV/UAT/PROD account resources from `config/organization.yml`.

Account creation uses a bootstrap-only SERVICE administrator with RSA public-key input supplied outside Git. Account resources have `prevent_destroy = true`. DEV/UAT/PROD routine roots do not use ORGADMIN.

### Per-account Terraform identity bootstrap

```text
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
```

are separate privileged lifecycles that create:

```text
DEV   SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
UAT   SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
PROD  SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Identity bootstrap may activate `ACCOUNTADMIN`; routine platform Terraform does not. Keeping identity state separate prevents normal automation from owning the resources needed to authenticate itself.

See ADR-021 and ADR-023.

## Routine account Terraform

Routine roots:

```text
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

activate only their environment-specific `AR_TERRAFORM_<ENV>` role. Initial account privileges are:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Real DEV plan/apply is the privilege-verification gate; static Terraform validation cannot prove Snowflake authorization sufficiency.

## Remote-state topology

The reference control-plane backend is S3 with encrypted state, native S3 lockfiles and bucket versioning.

State is separated from Snowflake account topology so a broken Snowflake account does not remove the state needed to recover it:

```text
organization
identity/dev
identity/uat
identity/prod
platform/dev
platform/uat
platform/prod
```

GitHub accesses the state bucket through AWS OIDC. Snowflake authentication independently uses GitHub OIDC WIF. No static AWS access key or routine Snowflake password/private key is part of the design.

See ADR-022 and `TERRAFORM_STATE_AND_IDENTITY.md`.

## Why CI stays in DEV

CI is ephemeral and repository-driven. A fourth CI account would add account-level identity/state/administration without enough benefit at this stage.

CI therefore shares the DEV account while remaining isolated through:

- `CI_<DOMAIN>` databases;
- PR-specific schemas;
- dedicated `WH_<DOMAIN>_CI` warehouses;
- later dedicated **project CI** workload identities;
- explicit cleanup lifecycle.

The platform-infrastructure Terraform identity is not the future project/dbt CI identity.

## Domain access model

Each domain has independent roles:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

`GUEST` is authenticated read-only consumer access and initially sees only:

```text
MARTS
SEMANTIC
```

`READER` sees all stable domain layers. Health roles never imply Transport access and vice versa.

See ADR-020 and `RBAC_MODEL.md`.

## DEV account

Stable development databases:

```text
DEV_HEALTH
DEV_TRANSPORT
```

Stable transformation schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Personal schemas are not Terraform-managed. Example inside `DEV_HEALTH`:

```text
ALICE_STAGING
ALICE_MARTS
```

CI databases:

```text
CI_HEALTH
CI_TRANSPORT
```

Terraform creates the CI databases but not ephemeral PR schemas. Delivery workflows later create/remove names such as `PR_123_STAGING`.

DEV domain warehouses:

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
AR_HEALTH_GUEST        -> WH_HEALTH_QUERY
AR_HEALTH_DEVELOPER    -> WH_HEALTH_TRANSFORM
AR_TRANSPORT_GUEST     -> WH_TRANSPORT_QUERY
AR_TRANSPORT_DEVELOPER -> WH_TRANSPORT_TRANSFORM
```

READER inherits GUEST query access. CI warehouses are reserved for later project CI identities.

Platform infrastructure automation uses:

```text
SU_GITHUB_TERRAFORM_DEV -> AR_TERRAFORM_DEV
```

The manual `Terraform Plan DEV` workflow is the first remote execution path, but it cannot run until the real S3/AWS OIDC and Snowflake WIF environment values are configured.

## UAT account

Databases:

```text
UAT_HEALTH
UAT_TRANSPORT
```

UAT is a separate production-like account so account-scoped RBAC, identity, integrations, parameters and operational configuration can be tested before PROD.

Warehouses:

```text
WH_HEALTH_QUERY
WH_HEALTH_TRANSFORM
WH_TRANSPORT_QUERY
WH_TRANSPORT_TRANSFORM
WH_PLATFORM_OPS
```

Human developers are read-only by default. GUEST receives query compute; domain ADMIN currently receives transform compute until project deployment workload identities are implemented.

Platform infrastructure automation uses `SU_GITHUB_TERRAFORM_UAT -> AR_TERRAFORM_UAT`, but no UAT remote plan/apply workflow is enabled until DEV is proven.

## PROD account

Databases:

```text
PROD_HEALTH
PROD_TRANSPORT
```

Warehouses:

```text
WH_HEALTH_QUERY
WH_HEALTH_TRANSFORM
WH_TRANSPORT_QUERY
WH_TRANSPORT_TRANSFORM
WH_PLATFORM_OPS
```

Query and transform compute are deliberately separated for workload isolation, cost attribution and operational control. Human developers remain read-only by default.

Platform infrastructure automation uses `SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD`. PROD planning/apply remains disabled until DEV and UAT are proven and GitHub Environment protection is in place.

## Database boundary and many physical sources

A domain may ingest many MSSQL, MySQL, API, file or streaming sources without creating one database per source.

Example:

```text
PROD_HEALTH
├── RAW_EHR_MSSQL          # later, when source onboarding requires it
├── RAW_BOOKING_MYSQL      # later
├── RAW_INSURANCE_API      # later
├── STAGING
├── INTERMEDIATE
├── CANONICAL
├── MARTS
└── SEMANTIC
```

The domain database is the ownership/storage/recovery boundary. Source-level cost attribution additionally uses warehouses, query tags and Snowflake usage/storage metadata.

## `PLATFORM_CONTROL`

Every account owns an independent `PLATFORM_CONTROL` database with:

```text
DEPLOYMENT
QUALITY
OBSERVABILITY
OPERATIONS
```

Account-local operational state avoids making DEV/UAT/PROD availability depend on a central cross-account control database. Cross-account reporting can aggregate later.

## Retention baseline

Analytics/control databases initially use one day of Time Travel retention for portability and cost control. Organization account deletion grace is separately configured: DEV/UAT currently 7 days and PROD 30 days.

## Ownership

- Organization bootstrap owns DEV/UAT/PROD account resources and uses isolated ORGADMIN authority.
- Identity bootstrap owns platform Terraform service users, WIF trust and `AR_TERRAFORM_<ENV>` roles.
- Routine account Terraform owns domain databases, stable schemas, domain warehouses, structural `PLATFORM_CONTROL`, capability roles, database roles and grants.
- Personal DEV and PR CI schema lifecycle is not long-lived Terraform state.
- dbt owns transformation relations inside domain databases in later phases.
- Human user lifecycle comes from enterprise identity/SSO/SCIM rather than employee records in Terraform.

## Apply gate

The source foundation is ready for the first real execution sequence:

1. provision the S3 state bucket/control plane with versioning, encryption and AWS OIDC IAM;
2. execute/import organization account bootstrap under controlled ORGADMIN;
3. execute DEV identity bootstrap under controlled ACCOUNTADMIN;
4. configure GitHub Environment `dev` variables, including the account-scoped Snowflake OIDC audience;
5. run/review the manual DEV remote plan;
6. add a protected DEV apply only after the plan is understood;
7. verify Snowflake objects/grants and adjust only demonstrated privilege gaps;
8. repeat for UAT, then protected PROD.
