# Operational Control Access Boundary

## Status

**Accepted v2 design; source/static implementation and DEV deployment wiring are complete. Live Snowflake authorization proof is still pending.**

The baseline is **domain-scoped read surfaces plus domain-fixed owner-rights write APIs** generated from environment project metadata. The DEV Platform Control workflow now renders and deploys one ordered bundle containing base state, bootstrap, generation/reset, config snapshots and all generated domain access surfaces.

Do not describe this boundary as live/production-proven until DEV WIF deployment and cross-domain denial tests actually succeed.

## Shared platform-owned state

Account-local control state includes:

```text
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT
PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECK_RESULT
PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP
PLATFORM_CONTROL.OPERATIONS.DATASET_LIFECYCLE
PLATFORM_CONTROL.OPERATIONS.DATASET_RESET

PLATFORM_CONTROL.CONFIG.DATASET_CONFIG_SNAPSHOT
```

These base tables are platform-owned. Project runtime/recovery roles do not receive unrestricted DML on them.

## Security requirement

Within one Snowflake account:

```text
HEALTH runtime/recovery
  may use HEALTH-scoped control surfaces
  must not read/write/invoke TRANSPORT-scoped surfaces

TRANSPORT runtime/recovery
  may use TRANSPORT-scoped control surfaces
  must not read/write/invoke HEALTH-scoped surfaces
```

The same property must derive from metadata for future domains without copied domain-specific SQL.

## Domain-scoped read path

For each configured project code, generated secure views expose only server-fixed domain/environment state. Current surfaces include the normal runtime views plus bootstrap/reset lifecycle views.

Examples:

```text
HEALTH_PIPELINE_CHECKPOINT
HEALTH_PIPELINE_RUN
HEALTH_PIPELINE_CHECK_RESULT
HEALTH_PIPELINE_BOOTSTRAP
HEALTH_DATASET_LIFECYCLE
HEALTH_DATASET_RESET

TRANSPORT_...
```

The predicate is fixed inside the generated object; callers do not supply `PROJECT_CODE` or `ENVIRONMENT` to select another domain.

## Domain-scoped write path

Generated owner-rights procedures fix project and environment in the procedure body. Current families include:

```text
<DOMAIN>_ADVANCE_PIPELINE_CHECKPOINT(...)
<DOMAIN>_PIPELINE_RUN_START(...)
<DOMAIN>_PIPELINE_RUN_FINISH(...)
<DOMAIN>_RECORD_PIPELINE_CHECK_RESULT(...)

<DOMAIN>_PIPELINE_BOOTSTRAP_START(...)
<DOMAIN>_PIPELINE_BOOTSTRAP_MARK_SNAPSHOT_LANDED(...)
<DOMAIN>_PIPELINE_BOOTSTRAP_MARK_VALIDATED(...)
<DOMAIN>_PIPELINE_BOOTSTRAP_COMMIT_HANDOFF(...)

<DOMAIN>_DATASET_RESET_START(...)
<DOMAIN>_DATASET_RESET_COMPLETE(...)

<DOMAIN>_REGISTER_DATASET_CONFIG_SNAPSHOT(...)
```

Important enforcement properties:

- no caller-controlled `P_PROJECT_CODE`;
- no caller-controlled `P_ENVIRONMENT`;
- runtime/reset/config operations are matched to server-fixed domain/environment;
- project roles receive only their own generated views/procedures;
- shared base-table mutation remains platform-owned;
- recovery uses a separate `AR_<DOMAIN>_RECOVERY` capability rather than ordinary developer/deploy privilege.

## Metadata-driven generation

The authoritative project list is:

```text
config/environments/<env>.yml -> projects
```

Renderers derive the domain surfaces for DEV/UAT/PROD:

```text
render_domain_access.py
render_domain_bootstrap_access.py
render_domain_reset_access.py
render_domain_config_access.py
```

`render_deployment_bundle.py` combines those generated surfaces with the ordered base SQL files into one deterministic deployment artifact. Missing base files or invalid project/environment identifiers fail closed.

## DEV deployment contract

`.github/workflows/platform-control-sql-deploy-dev.yml` now:

```text
validate protected DEV environment configuration
-> install pinned renderer dependency + Snowflake CLI
-> render config/environments/dev.yml into one PLATFORM_CONTROL bundle
-> statically assert every control family is present
-> request account-scoped GitHub OIDC token
-> verify Snowflake WIF identity
-> execute the complete bundle
-> verify base/config/domain views and procedures
```

The workflow no longer manually executes only the original checkpoint/run/check SQL subset.

Source/static CI contains a workflow-contract test so this wiring cannot silently regress to partial deployment.

## Ownership boundary

```text
Terraform
  PLATFORM_CONTROL database/schemas
  stable roles, workload identities and warehouses

platform-infra native SQL
  shared control tables
  generated domain-scoped views/procedures
  ordered deployment bundle

Framework
  reusable SQL/dbt helpers that call the approved domain-scoped contract

Domain repos
  dataset/source contracts, readable SQL and explicit recovery plans
```

One database object has one lifecycle owner; Terraform and native SQL must not fight over the same object.

## Static verification

`Platform Control SQL CI` proves the intended source shape, including:

- renderer unit tests;
- DEV/UAT/PROD bundle rendering;
- dependency order;
- generated runtime/bootstrap/reset/config surfaces;
- no direct shared-table domain DML grants;
- project/environment are server-fixed in write APIs;
- bootstrap transaction/generation guards;
- reset generation/retry guards;
- config snapshot conflict safety;
- DEV deployment workflow consumes the complete bundle.

Static rendering does **not** prove Snowflake authorization, owner-rights behavior or live grants.

## Explicit non-solutions

Do not adopt:

```text
unrestricted project-role DML on PLATFORM_CONTROL base tables
caller-supplied project/environment authorization
row-access policy alone for write authorization
human ADMIN as routine runtime identity
one-off Health/Transport control SQL
Framework-owned connector LSN/Kafka/API cursor state
```

## Remaining live DEV verification gate

Live DEV must still prove:

```text
complete bundle deploys successfully
HEALTH reads/writes only HEALTH control state
TRANSPORT reads/writes only TRANSPORT control state
cross-domain views/procedures are unavailable
project roles have no direct base-table DML
recovery roles can reset only their own domain
bootstrap/reset retry and generation behavior works in Snowflake
checkpoint advancement and target processing compose correctly
config snapshot registration is conflict-safe
platform operator access works as designed
```

This live evidence is tracked by platform issue #6. Until it passes, the source/static implementation is complete but runtime authorization remains unproven.
