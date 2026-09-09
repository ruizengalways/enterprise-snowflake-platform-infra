# Enterprise Snowflake Platform Infrastructure

Central platform-engineering repository for the Enterprise Snowflake reference platform.

## Start here

For a new conversation/session, read in this order:

1. [`docs/CURRENT_CONTEXT.md`](docs/CURRENT_CONTEXT.md) — current implementation state, verified CI, blockers and next actions.
2. [`docs/PROJECT_BLUEPRINT.md`](docs/PROJECT_BLUEPRINT.md) — canonical Hybrid Framework v2 architecture.
3. [`docs/architecture/OPERATIONAL_CONTROL_ACCESS.md`](docs/architecture/OPERATIONAL_CONTROL_ACCESS.md) — domain-scoped runtime/bootstrap/reset/config control boundary.
4. [`docs/architecture/DATASET_RESET_GENERATION.md`](docs/architecture/DATASET_RESET_GENERATION.md) — generation-aware recovery contract.
5. [`docs/architecture/PIPELINE_PATTERN_COVERAGE.md`](docs/architecture/PIPELINE_PATTERN_COVERAGE.md) — source/ingestion vs downstream pattern coverage.
6. [`docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`](docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md)
7. [`docs/architecture/ACCOUNT_TOPOLOGY.md`](docs/architecture/ACCOUNT_TOPOLOGY.md)
8. [`docs/architecture/RBAC_MODEL.md`](docs/architecture/RBAC_MODEL.md)
9. [`docs/architecture/REPOSITORY_LAYOUT.md`](docs/architecture/REPOSITORY_LAYOUT.md)
10. [`docs/runbooks/terraform-platform-bootstrap.md`](docs/runbooks/terraform-platform-bootstrap.md)

Architecture decisions are under `docs/adr/`. Historical ADRs may contain superseded v1 terminology only when their status explicitly says they have been replaced.

## Core rule

```text
Metadata = HOW TO RUN
SQL      = WHAT THE DATA MEANS
```

The v2 downstream Framework begins **after Bronze evidence is landed**. External source/connector state such as SQL Server LSNs, Kafka offsets, API cursors and source extraction scheduling is not Framework processing state.

## Five-repository architecture

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

This repository owns stable Snowflake platform/account infrastructure: organization/account bootstrap, domain databases/schemas, RBAC, warehouses, Terraform and project workload identities, remote-state adapter contracts, workspace/deployment permission boundaries, cost/governance foundations and structural `PLATFORM_CONTROL` lifecycle.

It does not own domain business SQL, dbt models, source simulation runtime, ingestion producer code or day-to-day employee identity membership.

## Snowflake topology

The reference topology uses three accounts:

```text
DEV
  DEV_HEALTH / CI_HEALTH
  DEV_TRANSPORT / CI_TRANSPORT
  PLATFORM_CONTROL

UAT
  UAT_HEALTH
  UAT_TRANSPORT
  PLATFORM_CONTROL

PROD
  PROD_HEALTH
  PROD_TRANSPORT
  PLATFORM_CONTROL
```

CI is isolated inside DEV, not a fourth account.

Stable domain schemas follow the Medallion-aligned contract:

```text
BRONZE
SILVER_STAGING
SILVER_INTERMEDIATE
SILVER_CANONICAL
GOLD_MARTS
GOLD_SEMANTIC
DQ
```

A domain database is an environment × governed data-product boundary, not a database per source connector.

## Metadata v2

Dataset policy is table-scoped and separates:

```text
load.strategy
materialization.type
runtime.mode
```

Standard load strategies are:

```text
full_refresh
append_only
incremental_merge
scd1
scd2
custom
```

Physical compute is resolved from logical workload names such as `transform`. Platform environment metadata maps each domain workload to the appropriate warehouse.

The old `load_strategy`, `scd1_merge`, `scd2_merge`, `scd2_snapshot` and `scd2_stream_task` vocabulary is not part of v2.

## Human and machine access

Human hierarchy:

```text
AR_<DOMAIN>_GUEST -> READER -> DEVELOPER -> ADMIN
```

Employees receive roles through enterprise IdP/SCIM or another approved provisioning system. Terraform defines permission structure, not employee membership.

Machine identities are separate:

```text
SU_GITHUB_<DOMAIN>_CI
  -> AR_<DOMAIN>_CI

SU_GITHUB_<DOMAIN>_DEPLOY
  -> AR_<DOMAIN>_DEPLOY

AR_<DOMAIN>_RECOVERY
  -> bounded domain recovery capability
```

All normal GitHub-to-Snowflake machine authentication uses Workload Identity Federation with repository/GitHub-Environment scoped subjects and account-scoped audiences.

## Terraform state

Ten independent lifecycle/state roots are maintained:

```text
organization
identity/dev
identity/uat
identity/prod
platform/dev
platform/uat
platform/prod
project-identity/dev
project-identity/uat
project-identity/prod
```

Per environment:

```text
identity/<env>
  -> platform/<env>
      -> project-identity/<env>
```

Remote-state backend is deployment-selectable:

```text
azurerm -> Azure Blob Storage
s3      -> Amazon S3
```

One deployment uses one authoritative writable backend. OneDrive/SharePoint can store human documents/evidence, not live Terraform state.

## `PLATFORM_CONTROL`

Platform Control stores account-local audit/runtime state separately from domain data:

```text
CONFIG.DATASET_CONFIG_SNAPSHOT

OPERATIONS.PIPELINE_CHECKPOINT
OPERATIONS.PIPELINE_RUN
OPERATIONS.PIPELINE_CHECK_RESULT
OPERATIONS.PIPELINE_BOOTSTRAP
OPERATIONS.DATASET_LIFECYCLE
OPERATIONS.DATASET_RESET
```

Domain projects use generated server-fixed views/procedures. They do not receive broad DML on shared base tables and cannot choose another domain by passing a caller-controlled project code.

The DEV deployment workflow renders and executes one ordered complete bundle containing base objects plus generated runtime/bootstrap/reset/config domain surfaces. Source/static CI verifies that this cannot regress to the original partial four-file deployment.

## Processing reset

Generation-aware reset is a **downstream processing reset**. It preserves valid Bronze evidence and clears only explicit reconstructable downstream tables.

Reference plans:

```text
Transport
  SILVER_CANONICAL.VEHICLE_STATUS_HISTORY
  SILVER_CANONICAL.VEHICLE_STATUS_HISTORY__ESF_EVENTS

Health
  SILVER_CANONICAL.PATIENT
```

The domain reset wrappers verify environment/database identity and reject prefixed PR/personal workspaces.

If Bronze evidence itself is corrupt, ingestion recovery is a separate operation.

## Framework and domain status

The clean Hybrid Framework v2 baseline is merged and consumed through immutable SHAs. Source/static CI proves:

- schema-v2 metadata contracts;
- offline dbt parse/materialization routing;
- SCD1/SCD2 source/static behavior contracts;
- mixed strategy support;
- Medallion/workload resolution;
- domain-scoped Platform Control renderers;
- ordered control-plane deployment bundle;
- generation-aware reset source contracts;
- Framework-free Health/Transport standalone fixtures;
- Terraform/RBAC/state shape.

This is **not live Snowflake proof**.

## Remaining gates

Two explicit platform issues track the remaining non-source work:

```text
#5  protect main/rulesets across all five repositories
#6  configure DEV WIF and prove the platform end to end
```

Issue #6 covers:

```text
real DEV WIF
Terraform apply / Platform Control deployment
cross-domain denial
PR workspace lifecycle
live Transport SCD2
live Health SCD1
live Dynamic Table
live generation/reset
framework-free standalone live proof
real external source/ingestion path
same-SHA DEV -> UAT -> PROD promotion after DEV succeeds
```

Do not make the currently unconfigured PR Workspace live job a required merge check until the GitHub Environment/Snowflake identity is operational.

Kafka Connector, direct Snowpipe Streaming and Openflow remain intentionally deferred until the live DEV foundation is proven.
