# RBAC Model

## Status

Phase 1 executable baseline. Domain-scoped human/capability roles, published-data guest access, database roles, and domain warehouse grants are implemented in Terraform. Machine deployment identities are intentionally deferred to the workload-identity step.

## Principles

1. Account roles describe human/workload capability inside one Snowflake account.
2. Database roles describe object access inside one domain database.
3. Every analytics database belongs to exactly one governed domain/data product.
4. Every domain receives independent role and compute boundaries.
5. `GUEST` is authenticated read-only consumer access to published data, not Snowflake `PUBLIC` and not anonymous access.
6. `ACCOUNTADMIN` is not a normal CI/CD or platform-engineering role.
7. UAT/PROD human developers are read-only by default.
8. CI compute belongs to future machine identities, not normal human developer roles.
9. Terraform-managed stable schemas retain platform lifecycle ownership; domain data roles receive privileges rather than silently taking Terraform object ownership.

## Platform account roles

```text
AR_PLATFORM_READER
        ↓
AR_PLATFORM_ENGINEER
        ↓
AR_PLATFORM_ADMIN
        ↓
SYSADMIN
```

The lower role inherits the capabilities above it. Platform authority does not imply Health or Transport authority.

## Domain account roles

Every domain gets an independent hierarchy:

```text
AR_<DOMAIN>_GUEST
        ↓
AR_<DOMAIN>_READER
        ↓
AR_<DOMAIN>_DEVELOPER
        ↓
AR_<DOMAIN>_ADMIN
        ↓
SYSADMIN
```

Current examples:

```text
AR_HEALTH_GUEST
AR_HEALTH_READER
AR_HEALTH_DEVELOPER
AR_HEALTH_ADMIN

AR_TRANSPORT_GUEST
AR_TRANSPORT_READER
AR_TRANSPORT_DEVELOPER
AR_TRANSPORT_ADMIN
```

A person can receive multiple independent domain roles. `AR_HEALTH_ADMIN` does not imply any Transport access.

## Domain database roles

Each domain database gets only its owning domain's hierarchy:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
        ↓
DR_<DOMAIN>_ANALYTICS_READ
        ↓
DR_<DOMAIN>_ANALYTICS_WRITE
        ↓
DR_<DOMAIN>_ANALYTICS_OWNER
```

Examples in `DEV_HEALTH`:

```text
DEV_HEALTH.DR_HEALTH_ANALYTICS_GUEST
DEV_HEALTH.DR_HEALTH_ANALYTICS_READ
DEV_HEALTH.DR_HEALTH_ANALYTICS_WRITE
DEV_HEALTH.DR_HEALTH_ANALYTICS_OWNER
```

`DEV_HEALTH` never receives Transport database roles. Terraform uses an explicit database -> domain mapping rather than a Cartesian product.

### GUEST

The narrow consumer role. It receives:

- database `USAGE`;
- schema `USAGE` only on configured published schemas;
- `SELECT` on current/future tables, views and semantic views in published schemas.

Initial published schemas:

```text
MARTS
SEMANTIC
```

GUEST does **not** receive access to `STAGING`, `INTERMEDIATE`, `CANONICAL`, future RAW source schemas, DDL privileges, or transform compute.

### READ

Inherits GUEST and can inspect all stable domain schemas. Baseline privileges add:

- schema `USAGE` across stable schemas;
- `SELECT` on current/future tables, views and semantic views across stable schemas.

### WRITE

Inherits READ and adds core schema DDL for ordinary dbt development:

- `CREATE TABLE`;
- `CREATE VIEW`;
- `CREATE STAGE`;
- `CREATE FILE FORMAT`;
- `CREATE SEQUENCE`.

Task/stream/procedure privileges are not pre-granted; approved patterns add them when required.

### OWNER

Inherits WRITE and represents the domain's highest governed database-access tier assigned to `AR_<DOMAIN>_ADMIN`.

`OWNER` is an access-tier name. It does not automatically transfer ownership of Terraform-managed database/schema resources away from the platform.

## Warehouse isolation

Every domain owns separate workload compute:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
```

DEV additionally has:

```text
WH_<DOMAIN>_CI
```

Current examples:

```text
WH_HEALTH_QUERY
WH_HEALTH_TRANSFORM
WH_HEALTH_CI
WH_TRANSPORT_QUERY
WH_TRANSPORT_TRANSFORM
WH_TRANSPORT_CI
```

The same logical warehouse names can appear in DEV/UAT/PROD because accounts are independent. This is intentional: account identifies environment; warehouse identifies domain + workload.

### Warehouse grants

```text
AR_<DOMAIN>_GUEST     -> WH_<DOMAIN>_QUERY
AR_<DOMAIN>_READER    -> inherits GUEST query compute
```

DEV adds:

```text
AR_<DOMAIN>_DEVELOPER -> WH_<DOMAIN>_TRANSFORM
```

UAT/PROD currently add:

```text
AR_<DOMAIN>_ADMIN     -> WH_<DOMAIN>_TRANSFORM
```

This human UAT/PROD transform access is transitional. Once workload identity exists, normal deployment compute moves to dedicated machine roles and human admin use becomes exceptional.

`WH_<DOMAIN>_CI` is not granted to human roles; it is reserved for CI workload identities.

## Environment policy

### DEV account

```text
GUEST     -> published read + QUERY
READER    -> all stable read + inherited QUERY
DEVELOPER -> WRITE + TRANSFORM + inherited read/query
ADMIN     -> OWNER + inherited developer capability
```

### UAT account

```text
GUEST     -> published read + QUERY
READER    -> all stable read
DEVELOPER -> read-only (no WRITE database-role grant)
ADMIN     -> OWNER + TRANSFORM
```

### PROD account

```text
GUEST     -> published read + QUERY
READER    -> all stable read
DEVELOPER -> read-only (no WRITE database-role grant)
ADMIN     -> OWNER + TRANSFORM
```

## Human users and guest users

`GUEST` is a role, not a Terraform-managed employee list. Human user lifecycle should come from the enterprise identity system (SSO/IdP/SCIM). A business consumer or external approved user receives only the appropriate domain `GUEST` role unless a broader role is justified.

Do not use the Snowflake `PUBLIC` role as the business guest-access model.

## Machine identities

Human authority and machine deployment identity are separate.

The next RBAC extension introduces workload identities for:

- Terraform plan/apply;
- project CI validation;
- project deployment/promotion;
- PR schema lifecycle.

Those identities receive only workflow-required privileges and never use `ACCOUNTADMIN` for routine work.

## Future refinements

Add only when a real phase requires them:

- WIF/OIDC workload identities;
- personal DEV schema provisioning;
- ephemeral PR schema ownership/cleanup;
- task/stream/procedure execution privileges;
- governance-policy administration;
- cost/resource-monitor administration;
- break-glass recovery roles.
