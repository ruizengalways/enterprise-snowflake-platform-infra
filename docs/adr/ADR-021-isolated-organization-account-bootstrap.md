# ADR-021 — Isolated Organization account bootstrap

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

DEV, UAT, and PROD Snowflake accounts must exist before normal account-level Terraform can create databases, roles, warehouses, and control-plane objects. Account creation requires organization-level authority and initial administrative user material, which is substantially more privileged than routine platform deployment.

Mixing `ORGADMIN` into the normal DEV/UAT/PROD roots would unnecessarily expand the blast radius of every infrastructure run.

## Decision

Create a separate Terraform root:

```text
terraform/stacks/organization/
```

It alone uses a Snowflake provider configured with the `ORGADMIN` role and manages the DEV/UAT/PROD `snowflake_account` resources from `config/organization.yml`.

The initial account administrator is a bootstrap-only SERVICE user authenticated with an RSA public key supplied outside source control. No private key, password, or admin email is committed.

Environment account resources use Terraform `prevent_destroy = true`. Account retirement is an explicit operational/architecture event, not an ordinary `terraform destroy` action.

DEV/UAT/PROD account roots remain separate and do not use ORGADMIN.

## Consequences

- Organization-level privilege is isolated from routine platform changes.
- Accounts can be created or imported into one authoritative bootstrap state.
- Initial bootstrap identity can later hand off routine work to WIF/OIDC machine identities.
- Accidental account deletion through normal Terraform workflow is blocked.
- Organization state must be stored separately from DEV/UAT/PROD state.
- Existing accounts can be imported rather than recreated when adopting the reference platform in an established organization.
