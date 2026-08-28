# Snowflake Account and Environment Topology

## Status

Phase 1 executable baseline. Terraform code exists; shared-account apply remains gated on remote state and workload authentication.

## Organisation topology

```text
Snowflake Organisation
├── NONPROD account
│   ├── ANALYTICS_DEV
│   ├── ANALYTICS_CI
│   ├── ANALYTICS_UAT
│   └── PLATFORM_CONTROL
└── PROD account
    ├── ANALYTICS_PROD
    └── PLATFORM_CONTROL
```

`PLATFORM_CONTROL` intentionally has the same database name in each account. Operational/runtime state remains account-local; cross-account rollups can be introduced later without making one account's control plane a hard runtime dependency of the other.

## NONPROD

### `ANALYTICS_DEV`

Stable project schemas:

```text
HEALTH_STAGING
HEALTH_INTERMEDIATE
HEALTH_CANONICAL
HEALTH_MARTS
HEALTH_SEMANTIC
TRANSPORT_STAGING
TRANSPORT_INTERMEDIATE
TRANSPORT_CANONICAL
TRANSPORT_MARTS
TRANSPORT_SEMANTIC
```

Personal developer schemas are not Terraform-managed. Phase 2/3 dbt/bootstrap logic will create names such as:

```text
ALICE_HEALTH_STAGING
ALICE_HEALTH_MARTS
BOB_TRANSPORT_STAGING
```

### `ANALYTICS_CI`

The database is Terraform-managed, but PR schemas are deliberately not declared as stable Terraform resources.

Future delivery workflows create and remove schemas such as:

```text
HEALTH_PR_123_STAGING
HEALTH_PR_123_MARTS
TRANSPORT_PR_123_STAGING
```

This keeps short-lived CI lifecycle out of long-lived Terraform state.

### `ANALYTICS_UAT`

Contains the same project-qualified stable layers as DEV. UAT is a promotion environment for an immutable project Git SHA, not a separate code branch.

### NONPROD warehouses

```text
WH_HEALTH_DEV
WH_HEALTH_CI
WH_HEALTH_UAT
WH_TRANSPORT_DEV
WH_TRANSPORT_CI
WH_TRANSPORT_UAT
WH_PLATFORM_OPS
```

CI warehouses are intentionally not granted to human project roles in the current baseline. They are reserved for the later CI workload identity.

## PROD

### `ANALYTICS_PROD`

Stable project schemas:

```text
HEALTH_STAGING
HEALTH_INTERMEDIATE
HEALTH_CANONICAL
HEALTH_MARTS
HEALTH_SEMANTIC
TRANSPORT_STAGING
TRANSPORT_INTERMEDIATE
TRANSPORT_CANONICAL
TRANSPORT_MARTS
TRANSPORT_SEMANTIC
```

Project qualification is mandatory because Health and Transport coexist in the same analytics database. See ADR-016.

### PROD warehouses

```text
WH_HEALTH_TRANSFORM
WH_HEALTH_QUERY
WH_TRANSPORT_TRANSFORM
WH_TRANSPORT_QUERY
WH_PLATFORM_OPS
```

Transform and query workloads are separated in PROD to make deployment/runtime compute and consumer query compute independently controllable and observable.

## `PLATFORM_CONTROL`

Both accounts create the structural schemas:

```text
DEPLOYMENT
QUALITY
OBSERVABILITY
OPERATIONS
```

Phase 1 creates only the database/schema structure. Runtime tables are added when the first real deployment, quality, observability, or recovery consumer exists; this avoids speculative table design.

## Retention baseline

Initial configuration uses one day of Time Travel retention for portability across Snowflake editions. Higher retention is a deliberate environment configuration change once account edition, recovery objectives, and storage cost are known.

## Ownership

- Terraform via a `SYSADMIN` provider alias owns analytics databases, stable schemas, warehouses, and the structural `PLATFORM_CONTROL` database/schemas.
- Terraform via `SECURITYADMIN` manages account-role hierarchy and grants.
- Personal DEV and PR CI schema lifecycle is not Terraform-owned.
- dbt owns transformation objects inside project schemas in later phases.

## Apply gate

The code is intentionally safe to validate without Snowflake credentials. Do not automate apply until:

1. a durable remote Terraform backend is selected and documented;
2. workload identity/WIF is configured;
3. account identifiers and trust are tested;
4. a reviewed plan is produced for NONPROD first.
