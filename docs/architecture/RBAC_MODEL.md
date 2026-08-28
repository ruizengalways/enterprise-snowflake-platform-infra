# RBAC Model

## Status

Phase 1 executable baseline. Human/capability roles and database roles are implemented in Terraform. Machine deployment identities are intentionally deferred to the workload-identity step.

## Principles

1. Account roles describe human/workload capability.
2. Database roles describe object access within one analytics database.
3. Platform capability and project capability remain independent.
4. `ACCOUNTADMIN` is not a normal CI/CD or platform-engineering role.
5. PROD developer access is read-only by default.
6. CI warehouse access belongs to a future machine identity, not normal human developer roles.
7. Terraform-managed stable schemas retain platform lifecycle ownership; project data roles receive privileges rather than silently taking Terraform object ownership.

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

The arrow means the lower role inherits the upper role's capabilities through Snowflake role grants.

`AR_PLATFORM_ADMIN` does not inherit Health or Transport admin roles. Platform/project authority remains independently assignable to humans.

## Project account roles

For each project:

```text
AR_<PROJECT>_READER
        ↓
AR_<PROJECT>_DEVELOPER
        ↓
AR_<PROJECT>_ADMIN
        ↓
SYSADMIN
```

Current projects:

```text
HEALTH
TRANSPORT
```

A person may be granted multiple independent roles, for example `AR_PLATFORM_ENGINEER` and `AR_HEALTH_ADMIN`, without either role implying the other.

## Database roles

Each analytics database receives the same project-local database-role hierarchy:

```text
DR_<PROJECT>_ANALYTICS_READ
        ↓
DR_<PROJECT>_ANALYTICS_WRITE
        ↓
DR_<PROJECT>_ANALYTICS_OWNER
```

Database role names can repeat across `ANALYTICS_DEV`, `ANALYTICS_CI`, `ANALYTICS_UAT`, and `ANALYTICS_PROD` because the database is part of the database-role identifier.

### READ

Baseline privileges on project-owned stable schemas:

- database `USAGE`;
- schema `USAGE`;
- `SELECT` on current and future tables;
- `SELECT` on current and future views;
- `SELECT` on current and future semantic views.

### WRITE

Inherits READ and adds the core schema DDL needed for normal dbt development:

- `CREATE TABLE`;
- `CREATE VIEW`;
- `CREATE STAGE`;
- `CREATE FILE FORMAT`;
- `CREATE SEQUENCE`.

Additional privileges such as task/stream/procedure creation are not pre-granted. They are added only when an approved implementation requires them.

### OWNER

Inherits WRITE and is the highest project database-access tier assigned to `AR_<PROJECT>_ADMIN`.

The name `OWNER` expresses the project's highest governed access tier; it does **not** transfer ownership of Terraform-managed database/schema resources away from the platform. Actual Snowflake ownership transfer is treated as a separate lifecycle decision because unmanaged ownership transfer can break Terraform authority and managed-access semantics.

## NONPROD mapping

```text
AR_<PROJECT>_READER
  -> DR_<PROJECT>_ANALYTICS_READ

AR_<PROJECT>_DEVELOPER
  -> DR_<PROJECT>_ANALYTICS_WRITE

AR_<PROJECT>_ADMIN
  -> DR_<PROJECT>_ANALYTICS_OWNER
```

The mapping is created in `ANALYTICS_DEV`, `ANALYTICS_CI`, and `ANALYTICS_UAT`.

Human warehouse baseline:

```text
AR_HEALTH_READER       -> WH_HEALTH_UAT
AR_HEALTH_DEVELOPER    -> WH_HEALTH_DEV
AR_TRANSPORT_READER    -> WH_TRANSPORT_UAT
AR_TRANSPORT_DEVELOPER -> WH_TRANSPORT_DEV
AR_PLATFORM_ENGINEER   -> WH_PLATFORM_OPS
```

Because role capabilities inherit upward, project admins inherit their developer/reader warehouse access.

`WH_HEALTH_CI` and `WH_TRANSPORT_CI` are not granted to human roles in this baseline.

## PROD mapping

PROD deliberately differs:

```text
AR_<PROJECT>_READER
  -> DR_<PROJECT>_ANALYTICS_READ

AR_<PROJECT>_DEVELOPER
  -> inherits READER only

AR_<PROJECT>_ADMIN
  -> DR_<PROJECT>_ANALYTICS_OWNER
```

This means a normal developer may inspect production according to the project reader policy but cannot write production data/model objects through the developer role.

Warehouse baseline:

```text
AR_HEALTH_READER     -> WH_HEALTH_QUERY
AR_HEALTH_ADMIN      -> WH_HEALTH_TRANSFORM
AR_TRANSPORT_READER  -> WH_TRANSPORT_QUERY
AR_TRANSPORT_ADMIN   -> WH_TRANSPORT_TRANSFORM
AR_PLATFORM_ENGINEER -> WH_PLATFORM_OPS
```

## Machine identities

Human authority and machine deployment identity are separate concepts.

The next RBAC extension will introduce workload identities for:

- Terraform plan/apply;
- project CI validation;
- project deployment/promotion;
- PR schema lifecycle.

Those identities will receive only the privileges needed by their workflow. They will not use `ACCOUNTADMIN`, and CI warehouses will be granted to the relevant machine roles rather than broad human roles.

## Future refinements

Add only when a real phase requires them:

- workload identity federation/OIDC;
- personal DEV schema provisioning;
- ephemeral PR schema ownership/cleanup;
- task/stream/procedure execution privileges;
- governance-policy administration;
- cost/resource-monitor administration;
- break-glass recovery role design.
