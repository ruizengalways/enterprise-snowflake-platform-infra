# ADR-025 — DEV personal and PR CI workspace lifecycle

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

Long-lived Terraform state should own stable databases, roles and warehouses, not every developer or PR-specific schema. At the same time, DEV personal work and PR CI need deterministic namespaces, least-privilege compute, cleanup and a path that works for future domains without hard-coded Health/Transport Terraform.

The previous DEV RBAC implementation still attached human domain roles to `CI_<DOMAIN>` databases through the generic database-role mapping. That contradicted the intended machine-only CI boundary.

## Decision

Separate stable human DEV access from PR CI machine access.

### Human DEV databases

Human domain roles attach only to:

```text
DEV_<DOMAIN>
```

DEV `AR_<DOMAIN>_DEVELOPER` inherits the domain `WRITE` database role. That `WRITE` role receives `CREATE SCHEMA` only on the corresponding `DEV_<DOMAIN>` database.

Personal schema convention:

```text
<DEVELOPER>_<LAYER>
```

This is a namespace/workspace convention, not a per-person security boundary. Because developers share the domain developer role, stronger individual isolation would require an identity-governed personal-role design rather than relying on a schema-name prefix.

### PR CI databases

Human GUEST/READER/DEVELOPER/ADMIN roles do not attach to:

```text
CI_<DOMAIN>
```

Instead DEV creates a separate machine capability:

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> USAGE + CREATE SCHEMA on CI_<DOMAIN>
  -> USAGE on WH_<DOMAIN>_CI
```

PR schema convention:

```text
PR_<NUMBER>_<LAYER>
```

PR schemas are transient, use zero-day Time Travel, and are explicitly dropped by the PR lifecycle. They are expected to be reproducible.

### Framework ownership

Platform Infra owns stable Snowflake permissions/roles/warehouses.

`enterprise-snowflake-data-project-framework` owns reusable workspace naming, identifier validation and guarded create/drop SQL rendering.

Project repos consume those framework primitives rather than copying scripts.

## Metadata-driven domain onboarding

Each environment's project metadata identifies query/transform/CI warehouse keys. Root Terraform derives grants from those keys instead of hard-coding Health and Transport role/warehouse pairs.

Adding a domain should therefore be primarily metadata/configuration plus the project's own repo, not a copy/paste Terraform branch.

## Consequences

- CI database access is machine-only by design.
- Personal DEV workspace creation does not require adding employee names to Terraform.
- A future project CI service identity still needs to be implemented and assigned `AR_<DOMAIN>_CI`.
- Personal schema naming does not claim security isolation among developers sharing the same domain developer role.
- PR cleanup logic is deterministic and prefix-guarded in the framework.
