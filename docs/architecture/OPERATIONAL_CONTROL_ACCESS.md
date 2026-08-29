# Operational Control Access Boundary

## Status

**Design/implementation gap identified by documentation/source audit on 2026-08-29.**

`PLATFORM_CONTROL.OPERATIONS` objects and framework SQL primitives exist in source/static CI, but project-runtime access to shared operational state is **not yet safely wired** into domain machine RBAC. Do not describe runtime control-plane access as live/complete until this boundary is implemented and verified.

## Current objects

Account-local operational state currently includes:

```text
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT
PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECK_RESULT
PLATFORM_CONTROL.OPERATIONS.ADVANCE_PIPELINE_CHECKPOINT(...)
```

The framework currently exposes primitives that can read/write those contracts, including:

```text
esf_checkpoint_read_sql()
esf_checkpoint_advance_call_sql()
esf_pipeline_run_start_sql()
esf_pipeline_run_finish_sql()
esf_record_check_result_sql()
```

The default checkpoint relation/procedure names point at `PLATFORM_CONTROL.OPERATIONS`.

## Current missing bridge

`AR_<DOMAIN>_DEPLOY` currently receives domain analytics WRITE, transform warehouse usage and the Snowflake-native Stream/Task/Dynamic Table privileges required for stable project delivery.

It does **not** currently receive a completed domain-scoped access path to shared `PLATFORM_CONTROL.OPERATIONS` state.

This is intentional until the cross-domain isolation model is explicit. Do not solve it by granting every project deployment role unrestricted `SELECT`/DML on all control tables.

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

## Why a broad grant is unsafe

The current checkpoint advancement procedure is an owner-rights procedure and accepts `P_PROJECT_CODE` from the caller. Granting a project role USAGE on that procedure without an additional domain guard would allow the caller to request another project's code.

Likewise, the run/check-result framework primitives currently generate direct DML to a supplied relation and include `project_code` as data. Broad table DML would therefore make domain isolation depend on caller convention rather than enforcement.

A row access policy alone is not sufficient for the write path: Snowflake documents that row access policies do not prevent rows from being inserted.

Current Snowflake references:

- Owner/caller stored-procedure rights: https://docs.snowflake.com/en/developer-guide/stored-procedure/stored-procedures-rights
- `INVOKER_ROLE()`: https://docs.snowflake.com/en/sql-reference/functions/invoker_role
- Row access policy behavior/limitations: https://docs.snowflake.com/en/user-guide/security-row-intro

Note that for an owner-rights stored procedure, Snowflake evaluates `INVOKER_ROLE()` as the procedure owner role rather than the external caller role. Do not assume a generic owner-rights procedure can safely infer the calling domain from that function.

## Required design properties

Any accepted implementation must provide all of the following:

1. **Domain-enforced reads.** A project runtime cannot read another project's checkpoint/run/check state.
2. **Domain-enforced writes.** A caller cannot insert/update another `project_code` merely by changing a parameter.
3. **Least privilege.** Project runtime does not receive unrestricted DML on the whole operational schema.
4. **Metadata-driven onboarding.** Adding a domain should derive the access boundary from platform project metadata, not copied Health/Transport SQL.
5. **Platform visibility.** Governed platform operations/monitoring can still inspect account-wide state.
6. **One owner.** Terraform/native SQL/framework responsibilities remain unambiguous.
7. **No preview-only dependency as the mandatory baseline.** A production reference should not require a preview security feature when a stable design is available.
8. **Framework contract stays simple.** Projects should not need to know platform security implementation details beyond their approved operational API/relation contract.

## Candidate implementation shapes

No option is accepted yet. Viable designs include:

### A. Domain-scoped read surface + owner-rights write APIs

Keep shared base tables, expose only domain-filtered read surfaces to project roles, and route mutations through owner-rights procedures whose allowed project/domain is fixed by the granted API rather than caller-supplied free text.

This can remain metadata-driven by generating the domain surfaces/API grants from configured project codes.

### B. Domain-specific operational storage

Physically separate project runtime state inside `PLATFORM_CONTROL` and aggregate it for platform monitoring.

This is simpler to reason about from a security perspective but creates more objects and aggregation work.

### C. Policy-protected reads + guarded write API

Use a stable row-access mechanism for reads and owner-rights procedures for writes. The write API must independently enforce the project boundary because row-access policies do not block arbitrary inserts.

## Explicit non-solutions

Do not adopt these shortcuts:

```text
grant every AR_<DOMAIN>_DEPLOY unrestricted DML on PLATFORM_CONTROL.OPERATIONS
trust caller-supplied project_code without server-side enforcement
use row access policy alone as insert authorization
reuse human ADMIN as the routine runtime principal
create one-off Health/Transport logic that cannot derive for future domains
```

## Verification gate

Before project runtime control state is considered complete, live DEV must prove at least:

```text
HEALTH can read/write its own checkpoint/run/check state
TRANSPORT can read/write its own checkpoint/run/check state
HEALTH attempts against TRANSPORT state are denied or invisible
TRANSPORT attempts against HEALTH state are denied or invisible
platform operator access works as designed
retry/idempotency semantics remain correct
checkpoint advancement still composes with target-DML transaction requirements
```

Until then, the framework SQL primitives are reusable building blocks, not proof of end-to-end project operational-state authorization.
