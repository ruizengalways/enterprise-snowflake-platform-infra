# PLATFORM_CONTROL Operational SQL Deployment

## Ownership boundary

Terraform owns the stable `PLATFORM_CONTROL` database and managed schemas. Native SQL in this directory owns operational tables and procedures inside `PLATFORM_CONTROL.OPERATIONS`.

Do not manage the same table/procedure in Terraform and native SQL at the same time.

The operational SQL lifecycle is deliberately separate from Terraform state because these objects evolve as database-native operational contracts and procedures. Do not wrap them in Terraform `local-exec`, `null_resource`, or similar imperative escape hatches.

## DEV deployment order

The DEV deployment workflow executes files in this explicit order on one Snowflake CLI connection:

1. `pipeline_checkpoint.sql`
2. `pipeline_run.sql`
3. `pipeline_check_result.sql`
4. `advance_pipeline_checkpoint.sql`

The table DDL is idempotent for initial creation. Procedure deployment uses the repository definition as the authoritative body.

DDL is not treated as one rollback-able transaction. Snowflake DDL has its own transaction semantics, so deployment is ordered and fail-fast instead of pretending a multi-file DDL release can be atomically rolled back.

## Authentication

`.github/workflows/platform-control-sql-deploy-dev.yml` reuses the account-scoped platform Terraform workload identity:

```text
SU_GITHUB_TERRAFORM_DEV
  -> AR_TERRAFORM_DEV
  -> GitHub environment: dev
```

GitHub issues a short-lived OIDC token with the account-scoped Snowflake audience. Snowflake CLI authenticates with `WORKLOAD_IDENTITY` / `OIDC`; no password or private key is stored.

The CLI account identifier is constructed as:

```text
<SNOWFLAKE_ORGANIZATION_NAME>-<SNOWFLAKE_ACCOUNT_NAME>
```

## Preconditions

Do not run the operational SQL deployment before:

1. `identity/dev` is applied and WIF is verified;
2. `platform/dev` is applied and `PLATFORM_CONTROL.OPERATIONS` exists;
3. the `dev` GitHub Environment contains the Snowflake organization/account/audience variables already required by Terraform plan;
4. the platform role has the expected ownership/DDL rights on `PLATFORM_CONTROL.OPERATIONS`.

There is intentionally no automatic deploy on push while the reference environment has not completed live bootstrap.

## Verification

The workflow verifies the authenticated user/role/account before deployment and queries `INFORMATION_SCHEMA` / `SHOW PROCEDURES` after deployment. A deployment is not considered live-proven until the workflow succeeds against a real DEV Snowflake account.

## Promotion

After DEV is live-proven, UAT and PROD should receive equivalent protected workflows that execute the same immutable Git SHA. Do not maintain environment-specific SQL branches.
