# Operational Control Access Boundary

## Status

**Accepted design; source/static implementation in progress as of 2026-08-29.**

The accepted baseline is **domain-scoped read surfaces plus domain-fixed owner-rights write APIs** generated from environment project metadata.

The source renderer and static isolation checks now exist on the implementation branch. The existing DEV operational SQL deployment workflow has not yet been wired to execute the generated access SQL, and no real Snowflake account has verified the boundary. Do not describe runtime control-plane access as live/complete until the deployment wiring and live DEV denial tests succeed.

## Current base objects

Account-local operational state includes:

```text
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT
PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECK_RESULT
PLATFORM_CONTROL.OPERATIONS.ADVANCE_PIPELINE_CHECKPOINT(...)
```

The framework exposes primitives that can read/write these contracts, including:

```text
esf_checkpoint_read_sql()
esf_checkpoint_advance_call_sql()
esf_pipeline_run_start_sql()
esf_pipeline_run_finish_sql()
esf_record_check_result_sql()
```

The shared base tables and generic platform procedure remain platform-owned objects. Project runtime roles must not receive unrestricted access to them.

## Security requirement

Within one Snowflake account:

```text
HEALTH runtime
  may read/write HEALTH operational state
  must not read/write TRANSPORT operational state

TRANSPORT runtime
  may read/write TRANSPORT operational state
  must not read/write HEALTH operational state
```

The same property must hold for future domains such as FINANCE without hand-written source-specific logic.

Platform operators may have broader governed access where required.

## Why broad grants are unsafe

The generic checkpoint advancement procedure is an owner-rights procedure and accepts `P_PROJECT_CODE` from the caller. Granting a project role USAGE on that procedure without an additional domain guard would allow the caller to request another project's code.

Likewise, the existing run/check-result framework primitives can generate direct DML to a supplied relation and include `project_code` as data. Broad table DML would therefore make domain isolation depend on caller convention rather than enforcement.

A row access policy alone is not sufficient for the write path: row access policies do not prevent rows from being inserted.

For owner-rights procedures, do not assume `INVOKER_ROLE()` can safely recover the external project role. The accepted design avoids that dependency entirely.

## Accepted design

### Read path

For each configured project code, generate secure views over the shared base tables:

```text
<DOMAIN>_PIPELINE_CHECKPOINT
<DOMAIN>_PIPELINE_RUN
<DOMAIN>_PIPELINE_CHECK_RESULT
```

Each view contains a server-fixed predicate:

```sql
WHERE PROJECT_CODE = '<DOMAIN>'
```

`AR_<DOMAIN>_DEPLOY` receives `SELECT` only on its three domain views, plus the required database/schema `USAGE` privileges.

It receives no `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE` or `REFERENCES` privilege on the shared operational base tables.

### Write path

For each configured domain, generate owner-rights procedures whose project and environment are fixed in the procedure body rather than accepted from the caller:

```text
<DOMAIN>_ADVANCE_PIPELINE_CHECKPOINT(...)
<DOMAIN>_PIPELINE_RUN_START(...)
<DOMAIN>_PIPELINE_RUN_FINISH(...)
<DOMAIN>_RECORD_PIPELINE_CHECK_RESULT(...)
```

Important enforcement properties:

- there is no caller-controlled `P_PROJECT_CODE` parameter;
- there is no caller-controlled `P_ENVIRONMENT` parameter;
- checkpoint MERGE keys always include the fixed domain;
- run-start MERGE matching includes fixed domain and environment, so one project cannot update another project's same-named run;
- run-finish UPDATE includes fixed domain and environment predicates;
- check-result INSERT always writes fixed domain and environment values;
- the project role receives `USAGE` only on its own generated procedures.

The generic base procedure may remain available to governed platform operators, but project deploy roles must not be granted it.

### Metadata-driven generation

The authoritative project list remains:

```text
config/environments/<env>.yml -> projects
```

`snowflake/control/operations/render_domain_access.py` reads that metadata and deterministically renders all domain views, write APIs and grants for DEV/UAT/PROD.

Adding a new domain therefore requires project metadata and normal RBAC/project identity configuration; it does not require copied Health/Transport SQL.

The renderer rejects project codes that are not safe unquoted Snowflake identifiers.

## Ownership boundary

Ownership remains intentionally split:

```text
Terraform
  PLATFORM_CONTROL database
  managed schemas
  stable roles / workload identities / warehouses

platform-infra native SQL
  operational base tables
  generic platform procedure
  generated domain read/write access surfaces

framework
  reusable SQL/dbt helpers that target the approved project operational contract

project repos
  domain metadata, datasets and business logic
```

Do not manage the same database object in both Terraform and native SQL.

## Static verification

`Platform Control SQL CI` verifies at least:

```text
renderer unit tests pass
DEV/UAT/PROD metadata all render successfully
no shared operational-table project DML grant is generated
project/environment are not exposed as caller-controlled write-API parameters
finish updates are project/environment constrained
invalid project identifiers are rejected
```

Static rendering proves the intended SQL shape. It does not prove Snowflake authorization semantics or successful live deployment.

## Explicit non-solutions

Do not adopt these shortcuts:

```text
grant every AR_<DOMAIN>_DEPLOY unrestricted DML on PLATFORM_CONTROL.OPERATIONS
trust caller-supplied project_code without server-side enforcement
use row access policy alone as insert authorization
reuse human ADMIN as the routine runtime principal
infer the external project role from owner-rights procedure role functions
create one-off Health/Transport logic that cannot derive for future domains
```

## Remaining integration work

Before this boundary can be called source-complete, the protected operational SQL deployment workflow must render the selected environment configuration and execute the generated SQL after the shared base objects are deployed.

The framework runtime helpers must then use the domain-scoped read/write contract rather than assuming project DML on shared base relations.

## Live DEV verification gate

Before project runtime control state is considered complete, live DEV must prove at least:

```text
HEALTH can read/write its own checkpoint/run/check state
TRANSPORT can read/write its own checkpoint/run/check state
HEALTH cannot see TRANSPORT rows through its read surfaces
TRANSPORT cannot see HEALTH rows through its read surfaces
HEALTH cannot invoke TRANSPORT write procedures
TRANSPORT cannot invoke HEALTH write procedures
project roles have no direct DML on shared operational tables
project roles cannot invoke the generic project_code-accepting checkpoint procedure
platform operator access works as designed
retry/idempotency semantics remain correct
checkpoint advancement still composes with target-DML transaction requirements
```

Until then, the source/static implementation is a security design baseline, not proof of end-to-end project operational-state authorization.
