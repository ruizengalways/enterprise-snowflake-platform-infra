# ADR-027 — Project PR-CI OIDC identity lifecycle

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

DEV platform Terraform now creates machine-only `AR_<DOMAIN>_CI` roles, CI database roles, and CI warehouses. A project PR workflow still needs a Snowflake service identity that can authenticate without a password/private key and receive only its domain CI role.

The service identity cannot safely live in the existing `identity/dev` root because that root executes before `platform/dev`, while the `AR_<DOMAIN>_CI` roles are created by `platform/dev`. Putting both in the earlier identity root would introduce a cross-state lifecycle/order conflict.

## Decision

Add a separate DEV project-identity lifecycle:

```text
terraform/stacks/project-identity/dev/
```

Execution order:

```text
identity/dev
  -> platform/dev
      -> project-identity/dev
```

`project-identity/dev` creates one Snowflake SERVICE user per configured data project and grants an **existing** `AR_<DOMAIN>_CI` role to it.

Current derived identities:

```text
SU_GITHUB_HEALTH_CI
  -> AR_HEALTH_CI
  subject: repo:ruizengalways/enterprise-snowflake-health-analytics:environment:ci

SU_GITHUB_TRANSPORT_CI
  -> AR_TRANSPORT_CI
  subject: repo:ruizengalways/enterprise-snowflake-transport-analytics:environment:ci
```

The service users use GitHub OIDC workload identity federation and the DEV account-scoped Snowflake OIDC audience. They have no account-level privileges and no human/domain role inheritance beyond the explicit CI role.

A generic `service-identity` module owns service-user WIF + assignment to an existing role. It deliberately does not create or expand that role.

## Configuration

DEV metadata contains shared project-CI identity settings:

```text
github_owner
github_environment
oidc_issuer
```

Project repository and domain code already exist in each project entry. Service-user name, role name, and GitHub OIDC subject are derived by convention.

## State

This lifecycle receives its own remote state key:

```text
enterprise-snowflake-platform-infra/project-identity/dev/terraform.tfstate
```

It does not share state with `identity/dev` or `platform/dev`.

## Consequences

- Health PR CI cannot authenticate as Transport CI and vice versa.
- Project CI does not need passwords/private keys.
- Platform Terraform identity is not reused as data-project CI identity.
- `platform/dev` must be applied and verified before project-CI identity bootstrap.
- UAT/PROD project deployment identities remain separate future lifecycles; do not reuse a DEV CI identity for promotion/deployment.
