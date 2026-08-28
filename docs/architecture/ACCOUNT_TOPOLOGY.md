# Snowflake Account and Environment Topology

## Status

Phase 1 executable baseline. The platform now targets three Snowflake accounts: DEV, UAT and PROD. Account-level Terraform apply remains gated on remote state and workload authentication.

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

Account isolation is used for lifecycle/security boundaries. Database isolation is used for environment × data-product ownership, storage/recovery boundaries and clearer cost attribution.

## Why CI stays in DEV

CI is ephemeral and repository-driven. A fourth CI account would add account-level identity/state/administration without enough benefit at this stage.

CI therefore shares the DEV account while remaining isolated through:

- `CI_<PROJECT>` databases;
- PR-specific schemas;
- dedicated CI warehouses;
- later dedicated machine identities;
- explicit cleanup lifecycle.

## DEV account

Stable development databases:

```text
DEV_HEALTH
DEV_TRANSPORT
```

Each uses stable transformation schemas:

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

Terraform creates the databases but not the ephemeral PR schemas. Future delivery workflows create/remove names such as `PR_123_STAGING` inside the owning project's CI database.

DEV warehouses:

```text
WH_HEALTH_DEV
WH_HEALTH_CI
WH_TRANSPORT_DEV
WH_TRANSPORT_CI
WH_PLATFORM_OPS
```

CI warehouses are reserved for later machine identities rather than broad human access.

## UAT account

Databases:

```text
UAT_HEALTH
UAT_TRANSPORT
```

UAT is intentionally a separate account so promotion can validate account-scoped RBAC, identities, integrations, parameters and operational configuration before production.

Human developers are read-only by default in UAT; project admins retain the governed owner tier. Deployment will use a separate machine identity.

Warehouses:

```text
WH_HEALTH_UAT
WH_TRANSPORT_UAT
WH_PLATFORM_OPS
```

## PROD account

Databases:

```text
PROD_HEALTH
PROD_TRANSPORT
```

PROD warehouses:

```text
WH_HEALTH_TRANSFORM
WH_HEALTH_QUERY
WH_TRANSPORT_TRANSFORM
WH_TRANSPORT_QUERY
WH_PLATFORM_OPS
```

Transform and query compute are separated in PROD so deployment/runtime compute and consumer query compute can be controlled and attributed independently.

## Database boundary and many physical sources

A project may ingest many MSSQL, MySQL, API, file or streaming sources without creating one database per source.

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

The project database is the ownership/storage/recovery boundary. Source-level cost attribution additionally uses warehouses, query tags and Snowflake usage/storage metadata. See ADR-019.

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

Initial configuration uses one day of Time Travel retention for portability across Snowflake editions. Higher retention is a deliberate environment/project setting after recovery objectives, edition and storage cost are known.

## Ownership

- Organization bootstrap owns creation of DEV/UAT/PROD accounts and requires narrowly controlled organization-level privilege.
- Account Terraform stacks own databases, stable schemas, warehouses, structural `PLATFORM_CONTROL`, account roles, database roles and grants.
- Personal DEV and PR CI schema lifecycle is not long-lived Terraform state.
- dbt owns transformation relations inside project databases in later phases.
- Human user lifecycle is expected to come from enterprise identity/SSO/SCIM rather than employee records in Terraform.

## Terraform stacks

```text
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

Each account eventually receives an independent remote-state and workload-identity boundary.

## Apply gate

Do not automate shared apply until:

1. durable remote Terraform state is selected and documented;
2. workload identity federation is configured;
3. target account identifiers/trust are tested;
4. a reviewed DEV plan is produced first;
5. DEV is verified before enabling UAT, then PROD.
