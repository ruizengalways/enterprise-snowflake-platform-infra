# PLATFORM_CONTROL Operational SQL Deployment

## Ownership boundary

Terraform owns the stable `PLATFORM_CONTROL` database and managed schemas. Native SQL in this directory owns operational tables, procedures and generated domain access surfaces inside `PLATFORM_CONTROL.OPERATIONS`.

Do not manage the same table/view/procedure in Terraform and native SQL at the same time.

The operational SQL lifecycle is deliberately separate from Terraform state because these objects evolve as database-native operational contracts and procedures. Do not wrap them in Terraform `local-exec`, `null_resource`, or similar imperative escape hatches.

## Domain-scoped access generation

Project deployment roles must not receive direct DML on the shared operational base tables.

Before deployment, render the selected environment's project access surface from the authoritative environment metadata:

```bash
python snowflake/control/operations/render_domain_access.py \
  --config config/environments/dev.yml \
  --output /tmp/platform-control-domain-access-dev.sql
```

The renderer creates, for every configured project code:

```text
<DOMAIN>_PIPELINE_CHECKPOINT
<DOMAIN>_PIPELINE_RUN
<DOMAIN>_PIPELINE_CHECK_RESULT

<DOMAIN>_ADVANCE_PIPELINE_CHECKPOINT(...)
<DOMAIN>_PIPELINE_RUN_START(...)
<DOMAIN>_PIPELINE_RUN_FINISH(...)
<DOMAIN>_RECORD_PIPELINE_CHECK_RESULT(...)
```

It also grants the corresponding `AR_<DOMAIN>_DEPLOY` role only the database/schema usage plus access to its own generated views/procedures. Project and environment are fixed server-side for writes; callers do not submit them.

## DEV deployment order

The DEV deployment path must execute these steps in this explicit order on one Snowflake CLI connection:

1. `pipeline_checkpoint.sql`
2. `pipeline_run.sql`
3. `pipeline_check_result.sql`
4. `advance_pipeline_checkpoint.sql`
5. the generated DEV domain-access SQL from `render_domain_access.py`

The table DDL is idempotent for initial creation. Procedure/view deployment uses the repository definition plus environment metadata as the authoritative source.

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
3. `project-identity/dev` has created the configured `AR_<DOMAIN>_DEPLOY` roles before generated grants are applied;
4. the `dev` GitHub Environment contains the Snowflake organization/account/audience variables already required by Terraform plan;
5. the platform role has the expected ownership/DDL/grant rights on `PLATFORM_CONTROL.OPERATIONS`.

There is intentionally no automatic deploy on push while the reference environment has not completed live bootstrap.

## Verification

Static CI renders DEV/UAT/PROD domain access and asserts that project/environment are server-fixed and that the generated contract does not grant project roles direct shared-table access.

The protected deployment workflow must verify the authenticated user/role/account before deployment and query `INFORMATION_SCHEMA` / grants after deployment. For every configured project it must verify three domain views and four domain procedures.

Live DEV must additionally prove both directions of cross-domain denial (for example, Health cannot access Transport surfaces and Transport cannot access Health surfaces) before the authorization boundary is considered production-proven.

The current implementation branch has source/static rendering and tests. The existing protected DEV workflow still needs the generated SQL execution/verification step wired into it; do not describe the domain access surface as deployed until that change and live verification succeed.

## Promotion

After DEV is live-proven, UAT and PROD should receive equivalent protected workflows that execute the same immutable Git SHA and render access from their own environment metadata. Do not maintain environment-specific SQL branches or copied per-domain SQL files.
