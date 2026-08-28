# RBAC Model

## Status

Phase 1 executable baseline. Domain-scoped human/capability roles, published-data GUEST access, database roles, domain warehouse grants, and per-account Terraform workload identities are implemented in Terraform source and static CI. Real Snowflake apply/privilege verification is still pending.

## Principles

1. Account roles describe human/workload capability inside one Snowflake account.
2. Database roles describe object access inside one domain database.
3. Every analytics database belongs to exactly one governed domain/data product.
4. Every domain receives independent role and compute boundaries.
5. `GUEST` is authenticated read-only consumer access to published data, not Snowflake `PUBLIC` and not anonymous access.
6. Human capability roles and machine automation roles are separate.
7. `ACCOUNTADMIN`, `SYSADMIN`, and `SECURITYADMIN` are not normal routine CI/CD execution roles.
8. UAT/PROD human developers are read-only by default.
9. CI compute belongs to machine identities, not normal human developer roles.
10. Terraform-managed stable schemas retain platform lifecycle ownership; domain data roles receive privileges rather than silently taking Terraform object ownership.

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

The lower role in the diagram inherits the capabilities above it. Platform authority does not imply Health or Transport authority.

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

The narrow consumer role receives:

- database `USAGE` only where published schemas exist;
- schema `USAGE` only on configured published schemas;
- `SELECT` on current/future tables, views and semantic views in published schemas.

Initial published schemas:

```text
MARTS
SEMANTIC
```

GUEST does **not** receive access to `STAGING`, `INTERMEDIATE`, `CANONICAL`, future RAW source schemas, DDL privileges, transform compute, or CI databases that publish no consumer schemas.

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

The same logical warehouse names can appear in DEV/UAT/PROD because accounts are independent. Account identifies environment; warehouse identifies domain + workload.

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
AR_<DOMAIN>_ADMIN -> WH_<DOMAIN>_TRANSFORM
```

This human UAT/PROD transform access is transitional. Project deployment/promotion identities will take ordinary deployment compute in a later delivery phase.

`WH_<DOMAIN>_CI` is not granted to human roles; it is reserved for project CI workload identities.

## Terraform machine identities

Platform-infrastructure Terraform has a separate machine identity per Snowflake account:

```text
DEV   SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
UAT   SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
PROD  SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

These are platform automation identities, not domain roles. They are bootstrapped in independent state roots under `terraform/stacks/identity/<env>/`.

Initial routine Terraform account privileges are deliberately explicit:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine DEV/UAT/PROD roots activate only their `AR_TERRAFORM_<ENV>` role. They do not activate `ACCOUNTADMIN`, `SYSADMIN`, or `SECURITYADMIN`.

Because `MANAGE GRANTS` is powerful, Terraform roles are:

- service-user only;
- not granted to humans or data pipelines;
- environment-specific;
- protected with `prevent_destroy` in identity bootstrap state;
- authenticated through GitHub OIDC WIF rather than a stored password/private key.

Identity bootstrap itself is exceptional: it may activate `ACCOUNTADMIN` to create the service user/role and trust relationship. It is separate from routine platform state so normal automation cannot destroy its own authentication path.

## GitHub OIDC trust

Snowflake service-user subjects are pinned to repository + GitHub Environment:

```text
DEV  repo:ruizengalways/enterprise-snowflake-platform-infra:environment:dev
UAT  repo:ruizengalways/enterprise-snowflake-platform-infra:environment:uat
PROD repo:ruizengalways/enterprise-snowflake-platform-infra:environment:prod
```

Each Snowflake account also receives an account-scoped OIDC audience supplied at bootstrap/deployment time. The shared `snowflakecomputing.com` audience is intentionally not used for these identities.

See ADR-023 and `TERRAFORM_STATE_AND_IDENTITY.md`.

## Environment policy

### DEV account

```text
GUEST     -> published read + QUERY
READER    -> all stable read + inherited QUERY
DEVELOPER -> WRITE + TRANSFORM + inherited read/query
ADMIN     -> OWNER + inherited developer capability
```

Platform Terraform:

```text
SU_GITHUB_TERRAFORM_DEV -> AR_TERRAFORM_DEV
```

### UAT account

```text
GUEST     -> published read + QUERY
READER    -> all stable read
DEVELOPER -> read-only (no WRITE database-role grant)
ADMIN     -> OWNER + TRANSFORM
```

Platform Terraform:

```text
SU_GITHUB_TERRAFORM_UAT -> AR_TERRAFORM_UAT
```

### PROD account

```text
GUEST     -> published read + QUERY
READER    -> all stable read
DEVELOPER -> read-only (no WRITE database-role grant)
ADMIN     -> OWNER + TRANSFORM
```

Platform Terraform:

```text
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

## Human users and guest users

`GUEST` is a role, not a Terraform-managed employee list. Human user lifecycle should come from the enterprise identity system (SSO/IdP/SCIM). A business consumer or external approved user receives only the appropriate domain `GUEST` role unless a broader role is justified.

Do not use the Snowflake `PUBLIC` role as the business guest-access model.

## Other machine identities still deferred

Platform Terraform WIF is implemented in source. The following are separate identities to add only when their delivery lifecycle exists:

- project PR CI validation;
- project dbt deployment/promotion;
- PR schema lifecycle;
- ingestion runtime identities.

Those identities receive only workflow-required privileges and never use `ACCOUNTADMIN` for routine work.

## Verification gate

Static Terraform CI proves configuration/provider validity, not actual Snowflake privilege sufficiency. The first real DEV remote plan/apply must verify that `AR_TERRAFORM_DEV` can perform every Terraform-owned operation without widening to system roles. Any privilege expansion must be tied to a demonstrated resource requirement.

## Future refinements

Add only when a real phase requires them:

- personal DEV schema provisioning;
- ephemeral PR schema ownership/cleanup;
- project CI/deployment workload identities;
- task/stream/procedure execution privileges;
- governance-policy administration;
- cost/resource-monitor administration;
- break-glass recovery roles.
