# Enterprise Snowflake Platform — Current Context

Concise human handoff for a new conversation. Machine truth remains in Terraform/config/schema/SQL/tests.

## Current phase

The source/static foundation includes domain-scoped runtime/bootstrap control, Medallion topology, immutable config snapshots, metadata-driven SCD1/SCD2, thin deployment wrappers, generation-aware full reset, and now a **framework-independent data-repository portability contract**.

No real Snowflake DEV bootstrap, WIF authentication, Terraform apply, PLATFORM_CONTROL deployment, reset execution or live source handoff has been proven yet.

## Non-negotiable rules

- Domain data repositories have a portable core and are **not hosted by the framework**.
- Source contracts and synthetic source generation belong to the domain repo and must work without the enterprise framework.
- Framework/platform integration is an optional adapter around the domain core.
- Common technical behavior may be metadata-driven; genuine source/domain/business logic stays explicit.
- Do not turn YAML into a programming language.
- Git owns desired dataset configuration.
- `PLATFORM_CONTROL.CONFIG` is immutable deployment audit/readback state.
- `PLATFORM_CONTROL.OPERATIONS` is mutable runtime/recovery state.
- Domain isolation is enforced server-side through generated domain views / owner-rights procedures.
- Full reset is separate from repair/replay.
- Promote immutable reviewed Git SHAs; do not use DEV/UAT/PROD source branches.

See `docs/architecture/DATA_REPOSITORY_PORTABILITY.md`.

## Repository dependency direction

```text
portable domain repository core
  contracts
  domain metadata
  standalone synthetic Snowflake SQL
  domain docs
            ↑
optional enterprise adapter
  dbt/platform integration
  control-plane calls
  enterprise deploy/reset workflows
            ↑
enterprise framework + platform infra
```

Portable demo functionality must not require `PLATFORM_CONTROL`, Terraform, enterprise roles/warehouses/database names, GitHub WIF, the DEV/UAT/PROD topology, or a custom dbt package.

Current references:

```text
Transport PR #5
  DEMO_TRANSPORT.VEHICLE_STATUS_CDC
  DEMO_TRANSPORT.VEHICLE_STATUS_CURRENT
  DEMO_TRANSPORT.VEHICLE_POSITION_EVENTS
  Standalone SQL CI #1: SUCCESS

Health PR #4
  DEMO_HEALTH.PATIENT_CDC
  DEMO_HEALTH.PATIENT_DEMO_PROFILE
  DEMO_HEALTH.PATIENT_CURRENT
  Standalone SQL CI #1: SUCCESS
```

These standalone CIs run without the enterprise framework. A plain live Snowflake execution remains the portability live acceptance gate.

## Enterprise account/domain topology

```text
DEV account
  DEV_HEALTH
  CI_HEALTH
  DEV_TRANSPORT
  CI_TRANSPORT
  PLATFORM_CONTROL

UAT account
  UAT_HEALTH
  UAT_TRANSPORT
  PLATFORM_CONTROL

PROD account
  PROD_HEALTH
  PROD_TRANSPORT
  PLATFORM_CONTROL
```

Enterprise stable domain databases use:

```text
BRONZE
SILVER_STAGING
SILVER_INTERMEDIATE
SILVER_CANONICAL
GOLD_MARTS
GOLD_SEMANTIC
DQ
```

These are enterprise adapter conventions, not requirements of portable domain repositories.

## Platform control stack

```text
PR #1 feature/domain-scoped-operational-control
  runtime/checkpoint/run/quality/bootstrap domain APIs

PR #2 feature/medallion-dataset-control-plane
  Medallion + PLATFORM_CONTROL.CONFIG audit

PR #3 feature/dataset-reset-generation
  verified code head c20c09c0c5f51dff17ebc5fb3eec75c89c5ce5a2
  Terraform CI #167: SUCCESS
  Platform Control SQL CI #37: SUCCESS
```

PR #3 adds:

```text
DATASET_LIFECYCLE
DATASET_RESET
PIPELINE_CHECKPOINT    + GENERATION
PIPELINE_BOOTSTRAP     + GENERATION
PIPELINE_RUN           + GENERATION
PIPELINE_CHECK_RESULT  + GENERATION
AR_<DOMAIN>_RECOVERY
```

Reset semantics:

```text
ACTIVE generation N
  -> RESETTING
  -> explicit domain cleanup
  -> generation N+1 / READY_FOR_INITIAL_LOAD
  -> normal pipeline succeeds / checkpoint advances
  -> ACTIVE
```

Old generations remain auditable. Same reset ID is retryable only while `RESETTING`; ready/completed reset IDs fail closed before cleanup.

Recovery is intended for Senior Data Engineer+ without a mandatory multi-person approval chain. Domain Admin inherits Recovery. Recovery gets domain READ, domain table TRUNCATE and appropriate transform warehouse USAGE, but no direct mutation of shared PLATFORM_CONTROL base tables.

## Framework baseline

Optional enterprise adapter reset-aware framework pin:

```text
8afe208bd911a59b9334add78a53878ffea93087
Framework CI #181: SUCCESS
```

Framework PR stack:

```text
PR #2 metadata-driven SCD2
 -> PR #3 bootstrap
 -> PR #4 Medallion/config/deployment
 -> PR #5 bounded reset helpers
```

The framework accelerates enterprise operation. It is not a prerequisite for the portable source/demo capabilities in domain repos.

## Domain enterprise-adapter proof

Transport PR #4 reset integration:

```text
649021fa5f84e580361e86d9bf8c66664e581a04
dbt Static CI #53: SUCCESS
PR Workspace #34: blocked before Snowflake execution by missing approved ci environment configuration
```

Health PR #3 reset integration:

```text
d33f92a928e3c9ca553a843c2c52c4952d86a13b
dbt Static CI #34: SUCCESS
PR Workspace #15: blocked before Snowflake execution by missing approved ci environment configuration
```

Transport PR #5 and Health PR #4 sit above those reset integrations and add portable framework-free source simulation.

## Deployment boundary

Enterprise browser deploy remains:

```text
GitHub Actions -> Deploy -> choose dev / uat / prod
```

The reusable framework workflow verifies main history and immutable framework pin, validates metadata, derives dbt context, obtains WIF, runs `dbt build`, and registers config snapshots only after success.

This is one-click deployment of the selected current-main revision, not yet an exact same-SHA DEV -> UAT -> PROD promotion orchestrator.

## Static proof vs live proof

There are now two independent proof tracks:

```text
PORTABLE DOMAIN TRACK
  standalone SQL CI
  no framework/platform dependency
  source-contract shape checks

ENTERPRISE ADAPTER TRACK
  Terraform/control SQL/dbt static CI
  domain PLATFORM_CONTROL/RBAC/deployment/reset contracts
```

Static proof does not establish live WIF, Snowflake privilege behavior, `TRUNCATE`, cross-domain denial, transaction/concurrency semantics, real source CDC consistency, reset/reload execution or credits/performance.

## Next live gates

Enterprise gate:

```text
bootstrap DEV Snowflake + WIF
 -> Terraform apply
 -> deploy/verify PLATFORM_CONTROL
 -> prove HEALTH <-> TRANSPORT denial
 -> prove runtime/bootstrap/config
 -> prove Recovery + generation-aware reset
 -> connect one deterministic external-style source
 -> prove snapshot -> incremental/CDC handoff
```

Portable gate, independently:

```text
plain Snowflake database/account
no PLATFORM_CONTROL
no custom framework/dbt package
no enterprise roles or database naming
 -> execute Transport standalone SQL
 -> execute Health standalone SQL
 -> validate expected counts/keys/CDC operations
```

## Recommended merge order

```text
framework PR #2 -> #3 -> #4 -> #5
platform PR #1 -> #2 -> #3
Transport PR #1 -> #2 -> #3 -> #4 -> #5
Health PR #1 -> #2 -> #3 -> #4
```

Retarget stacked PRs to `main` as lower dependencies merge. Do not claim enterprise live deployment or plain-Snowflake portability live proof until the corresponding live gate is executed.
