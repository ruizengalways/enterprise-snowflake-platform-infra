# ADR-032 — PLATFORM_CONTROL Native SQL Lifecycle

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

`PLATFORM_CONTROL` contains two different lifecycle classes:

1. stable platform containers and access boundaries;
2. database-native operational contracts such as checkpoint tables, run/check ledgers and Snowflake Scripting procedures.

Managing every database-native object through Terraform would blur the declarative infrastructure boundary and encourage imperative escape hatches such as `local-exec`. Managing the same object through Terraform and SQL would also violate the one-object/one-owner principle.

## Decision

Terraform owns:

```text
PLATFORM_CONTROL database
PLATFORM_CONTROL managed schemas
RBAC/grants required to administer those containers
```

The platform repository's native SQL lifecycle owns operational objects inside those schemas, initially:

```text
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT
PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECK_RESULT
PLATFORM_CONTROL.OPERATIONS.ADVANCE_PIPELINE_CHECKPOINT(...)
```

Native SQL deployment is performed by a protected GitHub Actions workflow using Snowflake CLI and the existing account-scoped platform workload identity. It does not use passwords/private keys and does not use Terraform `null_resource`/`local-exec`.

The reference DEV workflow is manual until live account bootstrap has been completed. It:

1. obtains a short-lived GitHub OIDC token for the configured Snowflake audience;
2. authenticates Snowflake CLI with `WORKLOAD_IDENTITY` / `OIDC`;
3. verifies account/user/role;
4. executes the reviewed SQL files in explicit dependency order with fail-fast exit codes;
5. verifies the resulting objects.

## Transaction boundary

Do not describe a multi-file DDL release as atomic rollback. Snowflake DDL transaction semantics differ from ordinary DML. Operational SQL releases therefore use idempotent/forward-compatible DDL where practical, explicit ordering, fail-fast deployment and post-deploy verification.

Runtime DML transactions inside stored procedures/tasks remain separate and can be atomic where Snowflake supports them.

## Promotion

After DEV is live-proven, UAT and PROD receive protected equivalents that execute the same immutable repository SHA. Environment-specific SQL branches are prohibited.

## Consequences

- Terraform state remains focused on stable platform infrastructure.
- Operational database code has a clear authoritative owner and deployment path.
- SQL procedures can evolve naturally without hiding imperative behavior inside Terraform.
- Live deployment remains unproven until DEV identity/platform bootstrap succeeds and the workflow runs successfully against Snowflake.
