# Enterprise Snowflake Platform — Project Blueprint

> **Status:** Phase 1 in progress — platform/domain/workspace/project-CI plus reusable capture/checkpoint/quality/SCD foundations are implemented in source/static CI; live remote state + Snowflake apply/runtime verification remain.
>
> **Authority:** Canonical long-term architecture for the Enterprise Snowflake Platform.
>
> **Fast handoff:** Read [`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) first in a new conversation/session.

## 1. Goal

Build a production-grade reusable Snowflake platform/reference implementation suitable for real enterprise adoption and Senior/Principal Data Engineering / Snowflake Platform Engineering work.

A new governed domain should onboard by declaring bounded technical metadata and writing its real business SQL, not by copying infrastructure/capture/SCD mechanics.

## 2. Core principles

1. **Metadata drives stable technical behaviour.** Business joins, calculations, domain rules and genuinely different source semantics remain explicit code.
2. **Do not build a YAML programming language.** Metadata is a bounded contract, not an orchestration DSL.
3. **Git is desired-state/configuration source of truth.** `PLATFORM_CONTROL` stores mutable runtime/operational state.
4. **One object has one lifecycle owner.** Terraform, dbt, native SQL and runtime workflows must not fight over the same object.
5. **Promote immutable Git SHA.** Do not use DEV/UAT/PROD branches.
6. **Ingestion technology stops at the RAW contract.** Replacing Kafka/Openflow/Snowpipe Streaming must not force downstream redesign.
7. **Source fidelity is authoritative.** Downstream SCD code cannot recreate source changes that capture already collapsed.
8. **Classic Snowflake is the reliability baseline.** Dynamic Tables may optimize selected projections but every supported DT path must retain a classic alternative.
9. **Human and machine identities are separate.** Employee membership stays in enterprise identity systems.
10. **Least privilege before convenience.** Privilege expansion follows demonstrated requirements.
11. **Recovery, reconciliation, freshness, observability and cost attribution are design inputs.**
12. **Do not over-engineer ahead of a real consumer.** No empty placeholder directories or speculative abstractions.

## 3. Repository model

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

### Platform Infra

Owns Snowflake account/platform infrastructure, RBAC, warehouses, Terraform/WIF/state contract, workspace access boundaries, cost/governance/control-plane foundations and the lifecycle of native operational SQL inside `PLATFORM_CONTROL`.

### Data Project Framework

Owns reusable technical mechanics: metadata contracts/validation, dbt package/macros/tests, environment resolution, workspace/query-tag helpers, capture/checkpoint/SCD/quality mechanics and reusable delivery/recovery workflows.

### Domain Projects

Health/Transport own RAW contracts, dataset configuration, source definitions, business SQL/tests, marts, semantic definitions and ingestion-specific configuration.

### Demo Source Systems

Represents deterministic systems outside Snowflake and stops at the source/RAW boundary.

## 4. Snowflake account topology

```text
Snowflake Organization
│
├── DEV account
│   ├── DEV_HEALTH
│   ├── CI_HEALTH
│   ├── DEV_TRANSPORT
│   ├── CI_TRANSPORT
│   └── PLATFORM_CONTROL
│
├── UAT account
│   ├── UAT_HEALTH
│   ├── UAT_TRANSPORT
│   └── PLATFORM_CONTROL
│
└── PROD account
    ├── PROD_HEALTH
    ├── PROD_TRANSPORT
    └── PLATFORM_CONTROL
```

CI is not a fourth account. PR CI runs in DEV with separate CI domain databases and compute. UAT remains a real account so account-scoped identities/integrations/security/operations are proven before PROD.

## 5. Database and schema boundary

Database pattern:

```text
<ENVIRONMENT>_<DOMAIN>
```

Database means environment × governed data product/domain, not physical source system.

Stable schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Published schemas initially:

```text
MARTS
SEMANTIC
```

RAW source-purpose schemas appear only when a source is actually onboarded, for example `RAW_EHR_MSSQL`.

## 6. RAW contract and capture fidelity

The stable boundary is:

```text
External source
   -> ingestion implementation
      -> project-owned RAW contract
         -> staging
            -> intermediate/canonical
               -> marts
                  -> Semantic Views
```

The source onboarding matrix preserves common real-world capture cases such as full snapshot, watermark/lookback, tombstone, net/full CDC, transaction log, Debezium/Kafka, Delta CDF, business events, API cursor and file incrementals.

Framework implementation reduces those cases to reusable capture archetypes:

```text
snapshot
watermark
net_change
full_change
snapshot_diff
cursor_or_file
```

Capture fidelity is declared separately:

```text
current_state
net_change
full_change
full_event
```

Bounded capture metadata may include:

```text
archetype
fidelity
checkpoint_kind
ordering_columns
idempotency_columns
lookback_minutes   # watermark only
```

The validator prevents a contract from claiming stronger fidelity than the selected archetype supports.

### RAW preservation rules

A full snapshot is stored as immutable snapshot batches when delete inference, history, replay, reconciliation or audit is required. Destructive overwrite may exist as a current projection but must not be the only authoritative evidence.

Full-change/full-event sources append immutable source events to a regular Snowflake table before any Stream consumer. A Stream tracks a processing offset/delta and is not the complete event history store.

See ADR-031.

## 7. Human RBAC

Per-domain account role hierarchy:

```text
AR_<DOMAIN>_GUEST
        ↓
AR_<DOMAIN>_READER
        ↓
AR_<DOMAIN>_DEVELOPER
        ↓
AR_<DOMAIN>_ADMIN
```

Stable database roles:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
        ↓
DR_<DOMAIN>_ANALYTICS_READ
        ↓
DR_<DOMAIN>_ANALYTICS_WRITE
        ↓
DR_<DOMAIN>_ANALYTICS_OWNER
```

GUEST reads published MARTS/SEMANTIC only. READER reads stable layers. DEV DEVELOPER receives WRITE + transform compute. UAT/PROD DEVELOPER remains read-only by default. ADMIN is the highest governed domain access tier; it does not imply literal Terraform ownership transfer.

## 8. Employee identity model

Terraform manages what roles/grants exist, not who works at the company.

```text
Employee / contractor
   -> Entra ID / Okta group
      -> SCIM / approved identity provisioning
         -> AR_<DOMAIN>_<CAPABILITY>
```

Employee changes do not require Terraform modifications.

## 9. Domain compute

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV account only
WH_PLATFORM_OPS
```

Warehouse boundaries separate workload/concurrency/cost attribution. Environment metadata declares domain warehouse keys so new domains do not require copied root-Terraform grant blocks.

## 10. DEV personal workspaces

Human roles attach only to `DEV_<DOMAIN>`.

```text
<DEVELOPER>_<LAYER>
```

DEV WRITE receives `CREATE SCHEMA` on the owning DEV database. This is a namespace convention, not strong per-person security isolation.

## 11. PR CI workspaces

Human domain roles do not attach to `CI_<DOMAIN>`.

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> database USAGE + CREATE SCHEMA
  -> WH_<DOMAIN>_CI USAGE
```

PR convention:

```text
PR_<NUMBER>_<LAYER>
```

PR schemas are transient, zero-day Time Travel and guarded by strict prefix validation on cleanup.

## 12. Terraform lifecycle roots

Terraform selectively owns stable platform infrastructure. It does not own dbt models, employee membership or mutable pipeline progress.

```text
organization
identity/dev
identity/uat
identity/prod
platform/dev
project-identity/dev
platform/uat
platform/prod
```

Terraform baseline:

```text
Terraform CLI                 1.16.0
Snowflake Terraform provider  2.19.0
```

Each root commits a provider lock file and static CI uses read-only lock mode.

## 13. Platform Terraform identity

`organization/` alone uses ORGADMIN for controlled account create/import.

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Initial routine privileges:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine Terraform never activates ACCOUNTADMIN, SYSADMIN or SECURITYADMIN. Identity bootstrap may use ACCOUNTADMIN only to establish WIF and is isolated in separate state.

## 14. Project CI identity

After `platform/dev` creates domain CI capabilities, `project-identity/dev` creates only service users + role assignment:

```text
SU_GITHUB_HEALTH_CI    -> AR_HEALTH_CI
SU_GITHUB_TRANSPORT_CI -> AR_TRANSPORT_CI
```

GitHub OIDC subject is repository + GitHub Environment `ci`. Project CI identities receive no account-level privileges.

## 15. OIDC / WIF

Automation avoids Snowflake passwords/private keys. Platform subjects are repository + environment (`dev`, `uat`, `prod`); project CI subjects are their domain repository + `ci`.

Use account-scoped Snowflake OIDC audiences rather than the shared default audience.

## 16. Terraform remote state

The platform is not AWS-dependent.

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

Committed Snowflake roots remain backend-agnostic; execution materializes the selected backend with `terraform/scripts/select-backend.sh`. One deployment chooses one writable state backend.

## 17. Project metadata contracts

Framework schema version 1 covers project, dataset and project-owned RAW contracts.

Dataset metadata includes bounded technical fields such as:

```text
raw_contract
load_strategy
implementation
business_key
watermark_column
freshness
reconciliation
```

RAW contracts include source/entity/grain/key, columns/types/nullability/classification, timestamps, change semantics, capture archetype/fidelity/checkpoint/order/idempotency, cadence, retention and breaking-change policy.

Cross-file validation covers references, duplicate IDs/columns, nullable keys, keyed strategies, freshness order, source timestamps/CDC columns and strategy/capture compatibility.

Business joins, formulas, free-form SQL and arbitrary workflow branching do not belong in metadata.

## 18. Current first domain contracts

Health `patient`:

```text
source_system: ehr_mssql
load_strategy: scd2_merge
business_key: patient_id
watermark: source_updated_at
capture: full_change / full_change fidelity
ordering: source_sequence
idempotency: patient_id + source_sequence
change semantics: CDC + tombstone
freshness: 60/120 minutes
```

The old `scd2_snapshot` classification was corrected because this source contract is ordered full-change CDC, not a full table snapshot.

Transport `vehicle_position`:

```text
source_system: gtfs_realtime
load_strategy: append_only
business identity: vehicle_id
watermark: event_timestamp
capture: full_change / full_event fidelity
idempotency: vehicle_id + event_timestamp
change semantics: append
freshness: 5/15 minutes
```

These logical contracts exist before ingestion-specific implementation so later transport ingestion paths converge on the same RAW boundary.

## 19. dbt physical target resolution

Stable reference:

```text
dbt-core      1.12.3
dbt-snowflake 1.12.0
```

Resolver inputs:

```text
project_code
environment = dev | ci | uat | prod
workload    = query | transform | ci
optional developer identity
optional PR number
```

Outputs:

```text
ESF_PROJECT_CODE
ESF_ENVIRONMENT
ESF_SCHEMA_PREFIX
DBT_DATABASE
DBT_WAREHOUSE
DBT_DEFAULT_SCHEMA
```

Models use `ref()` / `source()` and must not hard-code environment databases. Human DEV defaults to external-browser authentication; machine targets use WIF/OIDC.

## 20. Metadata-to-dbt bridge and immutable pinning

`render_dbt_vars.py` validates project metadata before exposing bounded technical data under:

```text
esf_project
esf_datasets
```

Reusable offline dbt CI consumes those vars. Health and Transport use one aligned immutable framework revision for metadata action, dbt package, dbt static action and PR workspace workflow.

Current aligned baseline:

```text
2c3de742c2f9b3ca3dee3f7a84533b80350c1b7c
```

## 21. Basic standard load strategies

Approved vocabulary:

```text
full_refresh
append_only
incremental_merge
scd2_snapshot
scd2_merge
scd2_stream_task
```

Basic dbt materialization configuration covers:

```text
full_refresh       -> table
append_only        -> incremental append
incremental_merge  -> incremental merge + metadata business key
```

The model still owns its explicit SELECT/business logic. `append_only` does not invent a hidden source predicate. Dedicated SCD macros implement SCD behavior; the basic macro deliberately does not degrade SCD2 into generic dbt merge.

## 22. Checkpoint + runtime state

Mutable source progress is stored in:

```text
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT
```

It can represent watermark/cursor/source-position/event-offset/snapshot/file identity. Framework provides checkpoint read + advance call SQL; platform native SQL owns the advancement stored procedure.

Runtime attempt/check ledgers:

```text
PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECK_RESULT
```

`PIPELINE_RUN` tracks run attempt/status, Git SHA/query tag, checkpoints, row counts and error metadata. `PIPELINE_CHECK_RESULT` records structured technical quality/freshness/reconciliation outcomes. These tables never store business payloads as an observability shortcut.

## 23. SCD1 and SCD2

### SCD1 classic

`esf_scd1_merge_sql()` first reduces a change window to exactly one deterministic row per business key, then executes tombstone-aware current-state MERGE.

### SCD2 snapshot

`esf_scd2_snapshot_apply_sql()` performs correctness-first close + inferred-delete + insert logic in an explicit transaction. History guarantee is snapshot-granularity.

### SCD2 full change/event

`esf_scd2_event_history_select()` intervalizes immutable ordered events. `esf_scd2_rebuild_affected_keys_sql()` rebuilds only keys touched by the current batch from authoritative event history.

This affected-key rebuild is the default correctness-first `scd2_merge` algorithm because duplicate replay and late/out-of-order events can repair history. High-volume fast paths are allowed later only after proving equivalent invariants.

### SCD2 Stream/Task

`esf_scd2_stream_task_sql()` implements:

```text
immutable event table
 -> append-only Stream
 -> Triggered Task (NO_OVERLAP)
 -> transactionally capture affected keys
 -> replace affected SCD2 history
 -> commit
```

Each independent consumer owns its own Stream.

### SCD2 target/invariants

Target lifecycle helper adds:

```text
_ESF_VALID_FROM
_ESF_VALID_TO
_ESF_IS_CURRENT
_ESF_VERSION_ORDINAL
```

Generic violation queries/dbt tests cover multiple-current rows, invalid ranges, overlapping ranges and duplicate version ordinals.

Metadata validation rejects `scd2_snapshot` unless the source capture is a snapshot and rejects `scd2_stream_task` unless the capture is append-preserved full-change/full-event.

See ADR-031.

## 24. Dynamic Tables

Dynamic Tables are optional, not a required SCD2 mechanism.

The framework has optional SCD1/SCD2 DT projection wrappers, but callers must explicitly select refresh mode. Production does not default to `AUTO`.

Every supported DT path retains an equivalent regular-table/classic implementation. Window-heavy SCD2 DTs require workload benchmarks before adoption because valid incremental refresh can still recompute changed partitions and be expensive.

## 25. PR CI workflow safety

Reusable PR workspace workflow:

```text
PR opened/reopened/synchronize -> create idempotent PR_<n>_* schemas
PR closed                      -> guarded drop of PR_<n>_* schemas
```

It requests account-scoped GitHub OIDC and executes framework-generated workspace SQL only. It does not currently execute arbitrary untrusted PR business code while holding Snowflake credentials.

## 26. Query tags and cost attribution

Canonical JSON query-tag fields:

```text
required: project, environment, workload
optional: source, pipeline, dataset, run_id, git_sha, pr_number, operation
```

No personal/secret/regulated/business payload data belongs in query tags.

Cost boundaries:

```text
domain storage/recovery         -> <ENVIRONMENT>_<DOMAIN>
compute                         -> WH_<DOMAIN>_<WORKLOAD>
query execution attribution     -> QUERY_TAG + QUERY_ATTRIBUTION_HISTORY
warehouse idle compute          -> WAREHOUSE_METERING_HISTORY
serverless/ingestion            -> service-specific usage histories
fine storage                    -> Snowflake storage metrics/history
```

Query-attributed credits are not the full warehouse bill because idle warehouse compute is separate.

## 27. Data quality / reconciliation / freshness

Reusable primitives now include:

```text
metadata/schema validation
generic dbt tests
freshness age evaluation
row-count reconciliation
composite distinct-business-key reconciliation
source timestamp min/max reconciliation
structured check-result recording
pipeline run/attempt ledger SQL
```

Project-specific business quality rules stay in project tests.

## 28. PLATFORM_CONTROL lifecycle ownership

Terraform owns the stable `PLATFORM_CONTROL` database, managed schemas and surrounding access boundary.

Native platform SQL owns database-native operational tables/procedures within those schemas:

```text
PIPELINE_CHECKPOINT
PIPELINE_RUN
PIPELINE_CHECK_RESULT
ADVANCE_PIPELINE_CHECKPOINT(...)
```

Do not manage the same object through Terraform and SQL. Do not hide operational SQL inside Terraform `null_resource`/`local-exec`.

Reference DEV deployment:

```text
.github/workflows/platform-control-sql-deploy-dev.yml
```

The manual protected workflow uses Snowflake CLI 3.23.0 and the existing DEV platform OIDC/WIF identity, executes reviewed SQL files in explicit dependency order and verifies the result. DDL release is ordered/fail-fast rather than falsely described as one rollback-able transaction.

See ADR-032.

## 29. Observability and SLOs

Observe at minimum:

```text
ingestion freshness
pipeline/model run outcome
checkpoint progress
reconciliation status
DQ failures
warehouse/query usage
serverless ingestion usage
deployment/promotion outcome
recovery operations
```

SLO thresholds may be dataset/workload metadata when genuinely technical and repeatable.

## 30. Deployment and promotion

Target source promotion:

```text
feature branch / PR
   -> static validation
   -> isolated PR workspace validation
   -> merge immutable SHA
   -> DEV deployment
   -> UAT promotion of same SHA
   -> protected PROD promotion of same SHA
```

No environment branches. Platform Terraform, platform native operational SQL and data-project dbt identities are separate lifecycle concerns even when they reuse an appropriate account-scoped machine role.

UAT/PROD data-project promotion identities/workflows remain to be implemented.

## 31. Rollback and recovery

Derived PROD recovery pattern:

```text
pre-release zero-copy clone
   -> deployment
   -> verification
   -> controlled SWAP/restore if rollback required
```

Do not blindly roll back RAW ingestion state as if it were replaceable derived data.

Recovery distinguishes code rollback, derived-object/data rollback, replay/backfill, source correction and infrastructure recovery.

## 32. Semantic layer

Use native Snowflake Semantic Views as the governed semantic layer. No Cube dependency is planned. Semantic definitions remain domain-owned and are promoted/tested through the same project lifecycle.

## 33. Ingestion roadmap

Do not start ingestion demonstrations until live platform/framework foundations are credible.

Transport later compares:

```text
producer -> direct Snowpipe Streaming -> same RAW event contract
producer -> Kafka -> Snowflake Kafka Connector -> same RAW event contract
```

Normally only one comparison path is active at a time. Health later demonstrates Openflow where appropriate. Spark Streaming is introduced only if a real requirement cannot reasonably be met with Snowflake-native/Kafka paths. Marketplace Secure Shares are not a substitute for ingestion/streaming demonstrations.

## 34. New-domain onboarding target

A future Finance onboarding should require small declarative platform/project metadata rather than copied Terraform/capture/SCD code.

Expected standard resources include:

```text
DEV_FINANCE
CI_FINANCE
UAT_FINANCE
PROD_FINANCE

AR_FINANCE_GUEST
AR_FINANCE_READER
AR_FINANCE_DEVELOPER
AR_FINANCE_ADMIN
AR_FINANCE_CI

DR_FINANCE_ANALYTICS_GUEST/READ/WRITE/OWNER
DR_FINANCE_CI_WORKSPACE

WH_FINANCE_QUERY
WH_FINANCE_TRANSFORM
WH_FINANCE_CI
```

Employee counts do not change Terraform. Membership remains IdP/SCIM-driven.

## 35. Current verified source/static-CI status

Implemented and statically proven:

```text
3-account Terraform architecture
organization + Terraform WIF bootstrap roots
Azure Blob / S3 state adapters
domain databases/RBAC/GUEST/warehouses
DEV personal + machine-only CI workspace permissions
project-identity/dev source
project/dataset/RAW + capture fidelity metadata contracts
metadata validation reusable action
workspace + query-tag utilities
dbt target resolver + dbt package
Health/Transport thin dbt shells
metadata -> dbt vars bridge
basic full_refresh / append_only / incremental_merge config
capture latest-by-key / snapshot diff / tombstone current MERGE
checkpoint read + advancement contract
append-only Stream + Triggered Task SQL
pipeline run/check-result operational ledgers
freshness + reconciliation SQL
classic deterministic SCD1
snapshot SCD2
full-change affected-key SCD2
transactional Stream/Task SCD2
SCD2 target helper + invariant queries/dbt tests
optional Dynamic Table SCD1/SCD2 projections
strategy/capture compatibility validation
manual DEV platform-control native SQL deployment workflow source
cost-attribution diagnostic SQL
```

Latest framework static proof:

```text
Run:    33239329420
Commit: 2c3de742c2f9b3ca3dee3f7a84533b80350c1b7c
Result: SUCCESS
```

Latest aligned domain proof:

```text
Health Metadata:   33239490045  SUCCESS
Health dbt Static: 33239495036  SUCCESS
Transport Metadata:   33239509048  SUCCESS
Transport dbt Static: 33239513740  SUCCESS
```

Still live-unproven:

```text
remote state control plane
Snowflake account bootstrap/import
Terraform identity apply
DEV platform plan/apply
effective live privileges
platform-control native SQL deploy against DEV
project CI identity apply
real PR schema create/drop
live dbt execution/data correctness
checkpoint/run-ledger/quality runtime behavior
SCD replay/delete/reinsert/late-event behavior against live/fixture data
UAT/PROD data-project promotion identities
resource monitors/budgets/persisted cost views
```

## 36. Next implementation sequence

Without live cloud/Snowflake accounts:

```text
1. deterministic SCD2 behavioral fixture tests
2. reusable execution wrapper tying run ledger + checks + checkpoint commit together
3. canonical QUERY_TAG integration into dbt execution lifecycle
4. DEV data-project deployment identity/workflow contract
5. UAT/PROD promotion + recovery/clone/SWAP workflow contracts
```

When real infrastructure is available:

```text
choose Azure Blob OR S3
-> provision state + cloud OIDC
-> organization bootstrap/import
-> identity/dev apply
-> platform/dev plan/apply
-> Snowflake-side RBAC/object verification
-> platform-control SQL deploy DEV + verification
-> project-identity/dev apply
-> configure project GitHub Environment ci
-> real PR workspace test
-> live capture/checkpoint/SCD smoke tests
-> live dbt/basic-load smoke
-> UAT
-> protected PROD
```

## 37. Architecture decisions

Current key ADRs:

```text
ADR-018  three-account DEV/UAT/PROD topology
ADR-019  environment × domain database boundary
ADR-020  domain GUEST + workload warehouses
ADR-021  isolated ORGADMIN organization bootstrap
ADR-022  historical S3-only state choice — superseded
ADR-023  GitHub OIDC platform Terraform identity
ADR-024  Azure Blob/S3 Terraform state adapters
ADR-025  DEV personal + PR CI workspace lifecycle
ADR-026  query-tag + cost-attribution contract
ADR-027  project PR-CI OIDC identity lifecycle
ADR-028  project/dataset/RAW metadata contracts
ADR-029  dbt physical target resolution
ADR-030  basic metadata-driven dbt load strategies
ADR-031  capture fidelity + reusable SCD consumers
ADR-032  PLATFORM_CONTROL native SQL lifecycle
```
