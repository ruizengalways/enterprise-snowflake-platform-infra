# Snowflake Account and Environment Topology

## Status

Phase 1 executable baseline. The platform targets three Snowflake accounts: DEV, UAT and PROD. A separate Organization Terraform root now defines account creation, while routine account-level apply remains gated on remote state and workload authentication.

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

## Organization bootstrap

```text
terraform/stacks/organization/
```

is the only Terraform root using `ORGADMIN`. It manages DEV/UAT/PROD account resources from `config/organization.yml`.

Account creation uses a bootstrap-only SERVICE administrator with RSA public-key input supplied outside Git. Account resources have `prevent_destroy = true`. DEV/UAT/PROD routine roots do not use ORGADMIN.

See ADR-021.

## Why CI stays in DEV

CI is ephemeral and repository-driven. A fourth CI account would add account-level identity/state/administration without enough benefit at this stage.

CI therefore shares the DEV account while remaining isolated through:

- `CI_<DOMAIN>` databases;
- PR-specific schemas;
- dedicated `WH_<DOMAIN>_CI` warehouses;
- later dedicated CI workload identities;
- explicit cleanup lifecycle.

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

READER inherits GUEST query access. CI warehouses are reserved for later machine identities.

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

Human developers are read-only by default. GUEST receives query compute; domain ADMIN currently receives transform compute until deployment workload identity is implemented.

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
- Account Terraform stacks own domain databases, stable schemas, domain warehouses, structural `PLATFORM_CONTROL`, account roles, database roles and grants.
- Personal DEV and PR CI schema lifecycle is not long-lived Terraform state.
- dbt owns transformation relations inside domain databases in later phases.
- Human user lifecycle comes from enterprise identity/SSO/SCIM rather than employee records in Terraform.

## Terraform stacks

```text
terraform/stacks/organization/
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

Each root requires an independent remote-state boundary. Organization bootstrap is privileged and infrequent; DEV/UAT/PROD become routine WIF-authenticated roots.

## Apply gate

Do not automate shared apply until:

1. durable remote Terraform state is selected and documented for all four roots;
2. bootstrap admin inputs are handled through a controlled secret process;
3. workload identity federation is configured for routine account stacks;
4. target account identifiers/trust are tested;
5. a reviewed DEV plan is produced first;
6. DEV is verified before enabling UAT, then PROD.
