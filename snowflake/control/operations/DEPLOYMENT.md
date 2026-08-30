# PLATFORM_CONTROL Operational SQL Deployment

## Ownership boundary

Terraform owns the stable `PLATFORM_CONTROL` database and managed schemas. Native SQL in this directory owns operational tables, procedures and generated domain access surfaces inside `PLATFORM_CONTROL.OPERATIONS`.

Do not manage the same table/view/procedure in Terraform and native SQL at the same time.

The operational SQL lifecycle is deliberately separate from Terraform state because these objects evolve as database-native operational contracts and procedures. Do not wrap them in Terraform `local-exec`, `null_resource`, or similar imperative escape hatches.

## Preferred deployment entrypoint

Protected deployment workflows should consume one ordered generated bundle rather than reimplement SQL ordering in workflow YAML:

```bash
python snowflake/control/operations/render_deployment_bundle.py \
  --config config/environments/dev.yml \
  --output /tmp/platform-control-dev.sql
```

`render_deployment_bundle.py` is packaging only. It does not authenticate to Snowflake and contains no credentials. It assembles repository-owned base SQL and environment-generated domain surfaces in dependency order.

The lower-level renderers remain separate and are useful for focused tests and debugging:

```bash
python snowflake/control/operations/render_domain_access.py \
  --config config/environments/dev.yml \
  --output /tmp/platform-control-domain-access-dev.sql

python snowflake/control/operations/render_domain_bootstrap_access.py \
  --config config/environments/dev.yml \
  --output /tmp/platform-control-bootstrap-access-dev.sql
```

Keeping these generators separate prevents normal runtime control and one-time bootstrap handoff from becoming one oversized implementation.

## Generated domain surfaces

Project deployment roles must not receive direct DML on the shared operational base tables.

The normal operational renderer creates, for every configured project code:

```text
<DOMAIN>_PIPELINE_CHECKPOINT
<DOMAIN>_PIPELINE_RUN
<DOMAIN>_PIPELINE_CHECK_RESULT

<DOMAIN>_ADVANCE_PIPELINE_CHECKPOINT(...)
<DOMAIN>_PIPELINE_RUN_START(...)
<DOMAIN>_PIPELINE_RUN_FINISH(...)
<DOMAIN>_RECORD_PIPELINE_CHECK_RESULT(...)
```

The bootstrap renderer creates:

```text
<DOMAIN>_PIPELINE_BOOTSTRAP

<DOMAIN>_PIPELINE_BOOTSTRAP_START(...)
<DOMAIN>_PIPELINE_BOOTSTRAP_MARK_SNAPSHOT_LANDED(...)
<DOMAIN>_PIPELINE_BOOTSTRAP_MARK_VALIDATED(...)
<DOMAIN>_PIPELINE_BOOTSTRAP_COMMIT_HANDOFF(...)
```

Both generators grant `AR_<DOMAIN>_DEPLOY` only database/schema usage plus access to that domain's generated views/procedures. Project and environment are fixed server-side for writes; callers do not submit them.

The bootstrap control-plane design and acceptance criteria are documented separately in `docs/architecture/BOOTSTRAP_HANDOFF_CONTROL.md`.

## Deployment order encoded by the bundle

The bundle renderer owns this dependency order:

1. `pipeline_checkpoint.sql`
2. `pipeline_run.sql`
3. `pipeline_check_result.sql`
4. `pipeline_bootstrap.sql`
5. `advance_pipeline_checkpoint.sql`
6. generated normal domain operational access
7. generated bootstrap handoff access

`PIPELINE_BOOTSTRAP_COMMIT_HANDOFF` depends on `PIPELINE_CHECKPOINT`, so the checkpoint base table must exist before bootstrap procedures are created.

The table DDL is idempotent for initial creation. Procedure/view deployment uses repository definitions plus environment metadata as the authoritative source.

DDL is not treated as one rollback-able transaction. Snowflake DDL has its own transaction semantics, so deployment is ordered and fail-fast instead of pretending a multi-file DDL release can be atomically rolled back. The runtime handoff procedure itself uses an explicit transaction for the checkpoint + bootstrap-state commit.

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

Static CI renders DEV/UAT/PROD lower-level surfaces **and** complete ordered deployment bundles. It checks bundle dependency markers, project/environment server-fixing, absence of project direct shared-table DML grants, explicit bootstrap reconciliation gating, checkpoint-regression guards, and the handoff transaction shape.

The protected deployment workflow must verify the authenticated user/role/account before executing the generated bundle, then query `INFORMATION_SCHEMA` / grants afterward. For every configured project it must verify the normal operational views/procedures plus one bootstrap view and four bootstrap procedures.

Live DEV must additionally prove both directions of cross-domain denial, fail-closed bootstrap transitions, reconciliation failure rejection, checkpoint-regression rejection, idempotent retry behavior, and atomic handoff commit before the authorization/runtime boundary is considered production-proven.

The current implementation branch has source/static bundle rendering and tests. The existing protected DEV workflow still needs the bundle execution and post-deployment verification wired into it; do not describe these surfaces as deployed until that change and live verification succeed.

## Promotion

After DEV is live-proven, UAT and PROD should receive equivalent protected workflows that execute the same immutable Git SHA and render a bundle from their own environment metadata. Do not maintain environment-specific SQL branches or copied per-domain SQL files.
