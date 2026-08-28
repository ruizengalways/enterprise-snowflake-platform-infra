# ADR-017 — Terraform apply requires remote state and workload identity

- **Status:** Accepted
- **Date:** 2026-08-28

## Context

The Phase 1 Terraform code can be formatted and validated without credentials, but applying shared Snowflake infrastructure from local state or long-lived GitHub secrets would create avoidable state, credential, and recovery risk.

The final remote-state technology has not yet been selected, and the Snowflake/GitHub workload identity trust has not yet been implemented.

## Decision

Terraform CI is validation-only until both prerequisites exist:

1. a durable, access-controlled remote state backend with locking/versioning/recovery appropriate to the selected platform;
2. GitHub-to-Snowflake workload identity federation (or an equivalently short-lived approved mechanism) with dedicated execution roles.

Until then, CI runs only:

```text
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

No automated shared NONPROD or PROD apply is enabled.

The backend product is intentionally not guessed in source code. Selecting S3, Terraform Cloud/HCP Terraform, Azure storage, GCS, or another backend must reflect the actual hosting/security boundary rather than portfolio aesthetics.

## Consequences

- No authoritative shared infrastructure state is stranded on a developer machine.
- No long-lived private key/token is required merely to validate Terraform.
- The first real apply must be NONPROD and must use a reviewed plan.
- PROD apply remains impossible until the same state/auth controls are proven in NONPROD.
- Phase 1 is partially implemented before first apply, but not considered complete until these controls and an initial NONPROD deployment are proven.
