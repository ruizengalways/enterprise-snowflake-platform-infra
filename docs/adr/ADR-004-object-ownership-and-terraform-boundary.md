# ADR-004 — Object ownership and Terraform boundary

- **Status:** Accepted
- **Date:** 2026-08-28

## Context

Snowflake objects can be created by Terraform, dbt, SQL migrations or runtime processes. Allowing multiple systems to believe they authoritatively own the same object creates drift, destructive plans and unclear recovery responsibility.

## Decision

Adopt the rule: **one object has one authoritative owner**.

Terraform owns stable platform infrastructure and access-control objects such as databases, platform schemas, warehouses, account roles, database roles, grants, workload identities/integrations and central cost controls.

dbt owns project transformation relations, snapshots, tests and project-layer modelling objects.

Controlled Snowflake SQL owns selected native operational objects where it is a clearer lifecycle fit, such as procedures, tasks, alerts or recovery/control logic.

GitHub Actions orchestrates lifecycle but is not the declarative owner of Snowflake objects.

## Consequences

- Ownership must be documented when introducing a new object class.
- Terraform must not import/manage dbt-created relations merely for completeness.
- dbt must not create infrastructure objects already governed by Terraform.
- Recovery runbooks can identify the responsible code path and source of truth unambiguously.