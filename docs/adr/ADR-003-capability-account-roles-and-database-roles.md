# ADR-003 — Capability account roles plus database roles

- **Status:** Accepted
- **Date:** 2026-08-28

## Context

The platform needs to separate persona/workload capability from object-level database access and avoid employee-seniority role names. It also needs different write authority in NONPROD and PROD without maintaining different role naming systems.

## Decision

Use account roles for capability and database roles for object access.

Platform account roles:

```text
AR_PLATFORM_READER
AR_PLATFORM_ENGINEER
AR_PLATFORM_ADMIN
```

Project account roles:

```text
AR_<PROJECT>_READER
AR_<PROJECT>_DEVELOPER
AR_<PROJECT>_ADMIN
```

Database roles in each analytics database:

```text
DR_<PROJECT>_ANALYTICS_READ
DR_<PROJECT>_ANALYTICS_WRITE
DR_<PROJECT>_ANALYTICS_OWNER
```

Role inheritance is monotonic within a scope:

```text
READ -> WRITE -> OWNER
READER -> DEVELOPER -> ADMIN
```

In NONPROD, project developers receive WRITE. In PROD, project developers inherit READ only; Project Admin receives OWNER.

Platform roles and project roles remain independent. `AR_PLATFORM_ADMIN` does not automatically inherit every project admin role.

Custom top-level admin roles are granted to `SYSADMIN` so they remain reachable from the Snowflake system-role hierarchy. `ACCOUNTADMIN` is not the normal execution role.

## Consequences

- Human capability can be assigned independently from database object access.
- PROD developer write access is not accidentally inherited from NONPROD design.
- Database-role names can repeat safely across databases because the database qualifies the role.
- Machine deployment/CI identities can later receive narrowly scoped database/account roles without reusing human identities.
- Terraform-managed database/schema ownership is not silently transferred to project roles; ownership transfer requires an explicit lifecycle decision.
