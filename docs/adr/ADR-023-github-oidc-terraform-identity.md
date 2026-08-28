# ADR-023 — GitHub OIDC workload identity for routine Terraform

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

Routine Terraform must manage stable Snowflake platform objects without storing Snowflake passwords or private keys in GitHub. Granting the automation user `ACCOUNTADMIN`, `SYSADMIN`, or `SECURITYADMIN` for normal plans/applies would violate the platform's least-privilege boundary.

The identity that Terraform uses also cannot safely own its own bootstrap lifecycle in the same state: a bad routine change could otherwise remove or corrupt the credentials required to recover the stack.

## Decision

Create one Snowflake service user and one dedicated Terraform account role per Snowflake account:

```text
DEV   -> SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
UAT   -> SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
PROD  -> SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Each service user is `TYPE = SERVICE` and trusts GitHub's OIDC issuer:

```text
https://token.actions.githubusercontent.com
```

Subjects are pinned to this repository plus the matching GitHub Environment, for example:

```text
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:dev
```

The OIDC audience is deliberately not committed as the shared `snowflakecomputing.com` value. Each account must receive a non-empty account-scoped audience via deployment configuration, and GitHub must request a token with that exact audience.

Routine Terraform roles initially receive only the account-level privileges required by the current platform foundation:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Additional privileges are added only when a real Terraform-owned capability requires them.

## Bootstrap separation

The service user and routine role live in separate identity bootstrap roots:

```text
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
```

Identity bootstrap is a narrowly controlled privileged lifecycle and may use `ACCOUNTADMIN` during initial setup. Routine roots do not.

The routine roots use their environment-specific role through provider aliases:

```text
terraform/stacks/dev/  -> AR_TERRAFORM_DEV
terraform/stacks/uat/  -> AR_TERRAFORM_UAT
terraform/stacks/prod/ -> AR_TERRAFORM_PROD
```

The service user and its account role are protected with Terraform `prevent_destroy`.

## GitHub workflow boundary

A GitHub job using Snowflake WIF must:

1. run under the matching GitHub Environment (`dev`, `uat`, or `prod`);
2. have `id-token: write` and `contents: read` only unless more is explicitly required;
3. request a short-lived GitHub OIDC token with the account-scoped Snowflake audience;
4. expose that token to the Snowflake provider as `SNOWFLAKE_TOKEN` with `WORKLOAD_IDENTITY` / `OIDC` authentication;
5. use environment-scoped Snowflake organization/account identifiers;
6. never store a Snowflake password/private key as the normal CI credential.

## Consequences

- Compromise of DEV automation does not directly grant UAT/PROD Snowflake identity.
- PROD GitHub Environment protection can independently gate the PROD OIDC subject.
- Identity bootstrap remains intentionally more privileged than routine Terraform and must be rare/audited.
- `MANAGE GRANTS` is broad; therefore the routine role must not be shared with data pipelines or humans.
- Snowflake provider `2.19.0` requires the `USER_ENABLE_DEFAULT_WORKLOAD_IDENTITY` experiment when Terraform manages the service user's default workload identity. Keep that experiment confined to identity bootstrap roots.
