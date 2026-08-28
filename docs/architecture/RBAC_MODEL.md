# RBAC Model

## Status

Phase 1 executable baseline. Human/capability roles and project database roles are implemented in Terraform. Machine deployment identities remain the next workload-identity step.

## Principles

1. Account roles describe human/workload capability.
2. Database roles describe object access inside one project database.
3. Each analytics database maps to exactly one owning data product/project.
4. Platform capability and project capability remain independent.
5. `ACCOUNTADMIN` is not a normal CI/CD or platform-engineering role.
6. Human developers have WRITE in DEV only; UAT/PROD developer roles are read-only by default.
7. CI warehouse/database mutation belongs to a future machine identity.

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

`AR_PLATFORM_ADMIN` does not imply Health/Transport project administration.

## Project account roles

For each project in each account:

```text
AR_<PROJECT>_READER
        ↓
AR_<PROJECT>_DEVELOPER
        ↓
AR_<PROJECT>_ADMIN
        ↓
SYSADMIN
```

Current scopes are `HEALTH` and `TRANSPORT`.

## Database roles

Each project database receives only its owning project's hierarchy:

```text
DR_<PROJECT>_ANALYTICS_READ
        ↓
DR_<PROJECT>_ANALYTICS_WRITE
        ↓
DR_<PROJECT>_ANALYTICS_OWNER
```

Examples:

```text
DEV_HEALTH.DR_HEALTH_ANALYTICS_READ
UAT_HEALTH.DR_HEALTH_ANALYTICS_READ
PROD_TRANSPORT.DR_TRANSPORT_ANALYTICS_OWNER
```

`DEV_TRANSPORT` does **not** receive `DR_HEALTH_*` roles. Terraform consumes an explicit `database_projects` mapping instead of generating every project × database combination.

### READ

Baseline privileges:

- database `USAGE`;
- stable schema `USAGE`;
- `SELECT` on current/future tables;
- `SELECT` on current/future views;
- `SELECT` on current/future semantic views.

### WRITE

Inherits READ and adds ordinary dbt-development DDL on stable schemas:

- `CREATE TABLE`;
- `CREATE VIEW`;
- `CREATE STAGE`;
- `CREATE FILE FORMAT`;
- `CREATE SEQUENCE`.

Task/stream/procedure privileges are not pre-granted; they are added when a real pattern requires them.

### OWNER

Inherits WRITE and is the highest governed project tier assigned to `AR_<PROJECT>_ADMIN`.

`OWNER` is a capability name; it does not silently transfer ownership of Terraform-managed database/schema objects away from the platform lifecycle owner.

## DEV account mapping

Databases:

```text
DEV_HEALTH
CI_HEALTH
DEV_TRANSPORT
CI_TRANSPORT
```

Human role mapping:

```text
AR_<PROJECT>_READER
  -> DR_<PROJECT>_ANALYTICS_READ

AR_<PROJECT>_DEVELOPER
  -> DR_<PROJECT>_ANALYTICS_WRITE

AR_<PROJECT>_ADMIN
  -> DR_<PROJECT>_ANALYTICS_OWNER
```

Human warehouse baseline:

```text
AR_HEALTH_READER     -> WH_HEALTH_DEV
AR_TRANSPORT_READER  -> WH_TRANSPORT_DEV
AR_PLATFORM_ENGINEER -> WH_PLATFORM_OPS
```

Because roles inherit upward, developers/admins inherit reader warehouse access.

`WH_HEALTH_CI` and `WH_TRANSPORT_CI` are intentionally not granted to humans. Later CI workload identities receive the required CI database/schema/warehouse privileges.

## UAT account mapping

Databases:

```text
UAT_HEALTH
UAT_TRANSPORT
```

Human developer WRITE is disabled:

```text
AR_<PROJECT>_READER
  -> READ

AR_<PROJECT>_DEVELOPER
  -> inherits READ only

AR_<PROJECT>_ADMIN
  -> OWNER
```

Warehouses:

```text
AR_HEALTH_READER     -> WH_HEALTH_UAT
AR_TRANSPORT_READER  -> WH_TRANSPORT_UAT
AR_PLATFORM_ENGINEER -> WH_PLATFORM_OPS
```

Deployment writes will use a separate machine identity rather than broad human developer privileges.

## PROD account mapping

Databases:

```text
PROD_HEALTH
PROD_TRANSPORT
```

Developer WRITE remains disabled. Warehouse baseline:

```text
AR_HEALTH_READER     -> WH_HEALTH_QUERY
AR_HEALTH_ADMIN      -> WH_HEALTH_TRANSFORM
AR_TRANSPORT_READER  -> WH_TRANSPORT_QUERY
AR_TRANSPORT_ADMIN   -> WH_TRANSPORT_TRANSFORM
AR_PLATFORM_ENGINEER -> WH_PLATFORM_OPS
```

## Machine identities

Human authority and deployment identity are separate. The next RBAC extension will cover:

- Terraform plan/apply per account;
- project CI validation;
- project DEV/UAT/PROD deployment/promotion;
- PR schema lifecycle.

Those identities will use WIF/OIDC and least privilege rather than passwords or `ACCOUNTADMIN`.

## Human users

Human employee lifecycle is not expected to be a list of `snowflake_user` resources in this repository. Enterprise SSO/IdP/SCIM should provision/deprovision people; Terraform owns the platform role/grant model they are assigned into.
