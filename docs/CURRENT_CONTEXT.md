# Enterprise Snowflake Platform — Current Context

> **Purpose:** Fast handoff for a new conversation/session. Read this file first, then `PROJECT_BLUEPRINT.md` for long-term architecture.
>
> **Updated:** 2026-08-29
>
> **Current phase:** Phase 1 platform + reusable data framework foundation. Capture/checkpoint/quality/SCD source work is now implemented and static-CI proven; no live Snowflake account/platform apply or live data execution has happened yet.

## 1. Core rules

- Common technical behaviour is metadata-driven; genuine domain/business logic stays explicit SQL/code.
- Do not create a YAML programming language.
- No DEV/UAT/PROD Git branches; promote immutable Git SHA.
- One Snowflake object has one authoritative lifecycle owner.
- Git is configuration source of truth; `PLATFORM_CONTROL` is runtime/operational state.
- Human identity and machine identity are separate.
- Terraform defines stable roles/privileges/warehouses; Entra ID / Okta / SCIM controls employee membership.
- Recoverability, reconciliation, freshness, observability and cost attribution are first-class.
- Ingestion technology stops at the project-owned RAW contract.
- Dynamic Tables are optional only. Every supported DT path must retain a classic regular-table implementation.
- Do not start Kafka Connector, direct Snowpipe Streaming or Openflow demos before the platform/framework foundation is live-proven.

## 2. Repositories and ownership

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

- **platform-infra** — account/platform Terraform, RBAC, warehouses, state/WIF, workspace access, cost/governance and `PLATFORM_CONTROL` lifecycle.
- **data-project-framework** — metadata schemas/validation, workspace/query-tag utilities, dbt target resolution, capture/checkpoint/quality/SCD primitives, reusable CI/workflows.
- **demo-source-systems** — deterministic external-style source simulation only.
- **health/transport** — domain RAW contracts/config/business SQL/tests/semantic/ingestion configuration.

Project repos stay thin and consume immutable framework revisions.

## 3. Snowflake topology

```text
Snowflake Organization
├── DEV
│   ├── DEV_HEALTH
│   ├── CI_HEALTH
│   ├── DEV_TRANSPORT
│   ├── CI_TRANSPORT
│   └── PLATFORM_CONTROL
├── UAT
│   ├── UAT_HEALTH
│   ├── UAT_TRANSPORT
│   └── PLATFORM_CONTROL
└── PROD
    ├── PROD_HEALTH
    ├── PROD_TRANSPORT
    └── PLATFORM_CONTROL
```

CI is not a fourth account. Database = environment × governed domain/data product, not physical source.

Stable transform schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Published schemas initially: `MARTS`, `SEMANTIC`. RAW source-purpose schemas appear only when a real source is onboarded.

## 4. Human RBAC and compute

Per domain:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

Stable database roles:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
  -> READ
  -> WRITE
  -> OWNER
```

Policy:

- GUEST = authenticated MARTS/SEMANTIC read-only + query warehouse;
- READER = all stable-layer read;
- DEV DEVELOPER = WRITE + transform compute;
- UAT/PROD DEVELOPER = read-only by default;
- domain authority never implies another domain.

Employee lifecycle:

```text
Employee / contractor
  -> Entra ID / Okta group
  -> SCIM / approved provisioning
  -> AR_<DOMAIN>_<CAPABILITY>
```

Warehouses:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV account only
WH_PLATFORM_OPS
```

## 5. DEV personal + PR workspaces

Human roles attach to `DEV_<DOMAIN>`, never `CI_<DOMAIN>`.

Personal namespace:

```text
<DEVELOPER>_<LAYER>
```

Machine-only CI capability:

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> USAGE + CREATE SCHEMA on CI_<DOMAIN>
  -> USAGE on WH_<DOMAIN>_CI
```

PR schemas:

```text
PR_<NUMBER>_<LAYER>
```

Framework PR schemas are transient with zero-day Time Travel and prefix-guarded cleanup.

## 6. Machine identities

Platform Terraform:

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Project PR CI:

```text
SU_GITHUB_HEALTH_CI
  -> AR_HEALTH_CI
  -> repo:ruizengalways/enterprise-snowflake-health-analytics:environment:ci

SU_GITHUB_TRANSPORT_CI
  -> AR_TRANSPORT_CI
  -> repo:ruizengalways/enterprise-snowflake-transport-analytics:environment:ci
```

Platform/project automation uses GitHub OIDC + Snowflake Workload Identity Federation rather than passwords/private keys. Use account-scoped OIDC audiences.

## 7. Terraform lifecycle/state

Eight independent state objects:

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

Routine platform Terraform privileges initially:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine Terraform never activates ACCOUNTADMIN/SYSADMIN/SECURITYADMIN. Identity bootstrap may use ACCOUNTADMIN only to establish WIF; organization root alone uses ORGADMIN.

Versions:

```text
Terraform CLI                 1.16.0
Snowflake Terraform provider  2.19.0
```

Remote state adapters:

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

One deployment selects one writable backend. OneDrive/SharePoint may hold docs/audit artifacts, not live Terraform state.

## 8. RAW capture contract — 14 source cases reduced to 6 reusable archetypes

The source onboarding matrix preserves familiar real-world source/capture cases but maps implementation to six primitives:

```text
snapshot
watermark
net_change
full_change
snapshot_diff
cursor_or_file
```

Capture fidelity is separate:

```text
current_state
net_change
full_change
full_event
```

Bounded capture metadata includes:

```text
archetype
fidelity
checkpoint_kind
ordering_columns
idempotency_columns
optional watermark lookback
```

Source fidelity sets the maximum history guarantee. Downstream code cannot reconstruct source changes that upstream capture already collapsed.

Important RAW preservation rules:

- Full snapshot is preserved as immutable snapshot batches when delete inference/history/replay/audit is required. Destructive `OVERWRITE` may be a current projection, never the only evidence.
- Full-change/full-event capture first appends immutable events to a regular Snowflake table. A Stream is a delta/offset consumer, not the complete CDC history store.
- Metadata validation rejects impossible archetype/fidelity/checkpoint combinations and nullable business keys.

See ADR-031 and framework docs `capture-archetypes.md` / `source-capture-matrix.md`.

## 9. Checkpoint/runtime state

Mutable progress lives in:

```text
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT
```

It can represent:

```text
watermark
cursor
LSN / SCN / source position
event offset
snapshot_id
file identity
```

Framework macros:

```text
esf_checkpoint_read_sql()
esf_checkpoint_advance_call_sql()
```

Platform native procedure:

```text
PLATFORM_CONTROL.OPERATIONS.ADVANCE_PIPELINE_CHECKPOINT(...)
```

Checkpoint advancement happens after successful target processing; where atomicity is required, target DML and checkpoint advancement share an explicit transaction.

## 10. Runtime ledgers + quality primitives

Native operational tables now exist in source:

```text
PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECK_RESULT
```

`PIPELINE_RUN` records attempts, status, Git SHA/query tag, before/after checkpoints, row counts and error metadata. `PIPELINE_CHECK_RESULT` records structured technical freshness/reconciliation/check outcomes. Business/regulated payloads do not belong in these tables.

Framework runtime/quality macros include:

```text
esf_pipeline_run_start_sql()
esf_pipeline_run_finish_sql()
esf_freshness_check_sql()
esf_reconciliation_metrics_sql()
esf_reconciliation_compare_sql()
esf_record_check_result_sql()
```

Standard reconciliation supports row count, composite distinct business key, and source timestamp min/max. Project-specific DQ remains explicit project tests.

## 11. Classic capture execution primitives

Implemented reusable classic primitives include:

```text
esf_latest_observation()
esf_snapshot_diff()
esf_merge_current_state_sql()
esf_append_only_stream_sql()
esf_triggered_task_sql()
```

Triggered Task controls include minimum trigger interval, timeout, retry attempts, suspend-after-failures and explicit overlap policy. Shared work-table consumers use `NO_OVERLAP`.

## 12. SCD consumer architecture

SCD is downstream of capture fidelity.

### SCD1

```text
esf_scd1_merge_sql()
```

First reduces the incoming window to exactly one deterministic row per business key, then performs tombstone-aware current-state MERGE. This avoids nondeterministic multi-source-row target matches.

### SCD2 snapshot

```text
esf_scd2_snapshot_apply_sql()
```

Correctness-first transaction:

```text
close changed rows
close rows missing from the full snapshot (inferred delete)
insert new/current versions
commit
```

History fidelity is snapshot-granularity.

### SCD2 full change / full event

```text
esf_scd2_event_history_select()
esf_scd2_rebuild_affected_keys_sql()
```

Immutable ordered events are intervalized into history. Only affected keys are deleted/rebuilt in the SCD2 target. This is the default correctness-first `scd2_merge` algorithm because duplicate replay and late/out-of-order events can repair history from immutable RAW evidence.

### SCD2 Stream + Triggered Task

```text
esf_scd2_stream_task_sql()
```

Pattern:

```text
immutable event table
  -> append-only Stream
  -> Triggered Task (NO_OVERLAP)
  -> BEGIN TRANSACTION
       consume stream into affected-key work table
       delete affected history
       recompute/insert affected history from immutable event table
     COMMIT
```

Failure before commit rolls back target DML and does not successfully advance the Stream offset.

## 13. SCD2 target + invariants

Target initialization:

```text
esf_scd2_target_table_sql()
```

Framework columns:

```text
_ESF_VALID_FROM
_ESF_VALID_TO
_ESF_IS_CURRENT
_ESF_VERSION_ORDINAL
```

Reusable invariant violation queries/tests:

```text
esf_scd2_multiple_current_violations_sql()
esf_scd2_invalid_range_violations_sql()
esf_scd2_overlap_violations_sql()
esf_scd2_duplicate_version_violations_sql()
esf_scd2_invariant_summary_sql()

esf_scd2_one_current
esf_scd2_valid_ranges
esf_scd2_no_overlaps
esf_scd2_unique_version_ordinal
```

Behavioral fixtures still need live/fixture execution for duplicate replay, delete/reinsert, equal-timestamp ordering and late-event repair.

## 14. SCD strategy/capture validation

Metadata CI now rejects structurally misleading combinations:

- `scd2_snapshot` requires `capture.archetype=snapshot`;
- `scd2_stream_task` requires `full_change`/`full_event` fidelity and an append-preserved event capture archetype;
- all SCD2 strategies require capture metadata.

`scd2_merge` can consume captured observed changes, but its history guarantee is still limited by source fidelity.

This is technical contract validation, not business logic in YAML.

## 15. Dynamic Table policy

Dynamic Tables are optional projection/execution choices, never platform dependencies.

Framework provides:

```text
esf_dynamic_table_projection_sql()
esf_scd1_dynamic_table_sql()
esf_scd2_dynamic_table_sql()
```

Callers explicitly choose refresh mode; `AUTO` is not the production framework default.

Classic equivalents always remain deployable. Window-heavy SCD2 DTs must be benchmarked because incremental refresh can still recompute changed partitions and become expensive.

## 16. Current domain contracts

### Health `patient`

```text
source_system:       ehr_mssql
load_strategy:       scd2_merge
business_key:        patient_id
watermark:           source_updated_at
capture archetype:   full_change
fidelity:            full_change
checkpoint:          source_position
ordering:            source_sequence
idempotency:         patient_id + source_sequence
change semantics:    CDC + tombstone delete
freshness:           warn 60 min / error 120 min
contract policy:     versioned_contract
```

The prior `scd2_snapshot` label was corrected because the RAW contract is ordered full-change CDC, not a full table snapshot.

### Transport `vehicle_position`

```text
source_system:       gtfs_realtime
load_strategy:       append_only
business identity:   vehicle_id
watermark:           event_timestamp
capture archetype:   full_change
fidelity:            full_event
checkpoint:          source_position
idempotency:         vehicle_id + event_timestamp
change semantics:    append
freshness:           warn 5 min / error 15 min
contract policy:     versioned_contract
```

Transport ingestion technology remains deferred. Direct Snowpipe Streaming and Kafka Connector paths must later converge on this same logical RAW contract.

## 17. dbt physical target + metadata bridge

Stable references:

```text
dbt-core      1.12.3
dbt-snowflake 1.12.0
```

Resolver inputs:

```text
project_code
environment = dev | ci | uat | prod
workload    = query | transform | ci
optional developer
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

Models use `ref()` / `source()` rather than hard-coded environment databases. Profiles contain no passwords/private keys. `render_dbt_vars.py` validates the project tree and exposes only bounded technical metadata under `esf_project` / `esf_datasets`.

## 18. Basic load configuration

`esf_configure_dataset()` covers the simple dbt-native strategies:

```text
full_refresh       -> table
append_only        -> incremental append
incremental_merge  -> incremental merge + metadata business key
```

Dedicated SCD macros implement SCD behavior; the basic materialization macro deliberately does not pretend SCD2 is generic incremental MERGE.

## 19. Framework immutable revision alignment

Health and Transport are now aligned on:

```text
2c3de742c2f9b3ca3dee3f7a84533b80350c1b7c
```

The same SHA is used by metadata validation action, dbt package, dbt static action and PR workspace workflow. This prevents hidden shared-capability drift.

## 20. PLATFORM_CONTROL object lifecycle

Ownership boundary:

```text
Terraform
  -> PLATFORM_CONTROL database
  -> managed schemas / stable access boundary

platform native SQL
  -> operational tables/procedures inside PLATFORM_CONTROL
```

Native SQL currently owns:

```text
PIPELINE_CHECKPOINT
PIPELINE_RUN
PIPELINE_CHECK_RESULT
ADVANCE_PIPELINE_CHECKPOINT(...)
```

The manual DEV workflow:

```text
.github/workflows/platform-control-sql-deploy-dev.yml
```

uses Snowflake CLI 3.23.0 + the existing DEV platform OIDC/WIF identity, executes files in explicit order and verifies resulting objects. It is intentionally not automatic until DEV bootstrap is live-proven. No Terraform `null_resource`/`local-exec` is used.

See ADR-032 and `snowflake/control/operations/DEPLOYMENT.md`.

## 21. Query tags + cost attribution

Required query-tag keys:

```text
project
environment
workload
```

Optional:

```text
source
pipeline
dataset
run_id
git_sha
pr_number
operation
```

No personal/secret/regulated/business payload data.

Cost model:

```text
Domain storage/recovery         -> <ENVIRONMENT>_<DOMAIN>
Compute                         -> WH_<DOMAIN>_<WORKLOAD>
Per-query execution attribution -> QUERY_TAG + QUERY_ATTRIBUTION_HISTORY
Warehouse idle compute          -> WAREHOUSE_METERING_HISTORY
Serverless/ingestion            -> service-specific usage histories
Fine storage detail             -> Snowflake storage histories/metrics
```

Baseline SQL: `snowflake/monitoring/queries/cost_attribution.sql`.

## 22. Verified CI

### Platform Terraform

```text
Run:    33223588208
Commit: 509f2986dd9b74f063e7f65b4dfcf8d7655cf5ed
Result: SUCCESS
```

This is the last referenced Terraform static proof; later platform SQL/docs commits do not change Terraform roots.

### Framework capture/checkpoint/quality/SCD baseline

```text
Run:    33239329420
Commit: 2c3de742c2f9b3ca3dee3f7a84533b80350c1b7c
Result: SUCCESS
```

Both framework jobs succeeded. Static proof covers metadata validation, target/dbt vars, capture SQL, checkpoint SQL, freshness/reconciliation SQL, pipeline run ledger SQL, deterministic SCD1, snapshot/full-change SCD2, transactional Stream/Task SCD2 and DT wrapper rendering.

### Health final aligned project CI

```text
Metadata CI:   33239490045  SUCCESS
dbt Static CI: 33239495036  SUCCESS
```

### Transport final aligned project CI

```text
Metadata CI:   33239509048  SUCCESS
dbt Static CI: 33239513740  SUCCESS
```

Static CI proves source/schema/package/macro/config validity, not live Snowflake authorization or runtime data correctness.

## 23. What has NOT happened yet

Do not claim these are complete:

- no real Azure Blob/S3 state control plane provisioned;
- no Snowflake DEV/UAT/PROD account bootstrap/import executed by Terraform;
- no Terraform identity root applied to live Snowflake;
- no real DEV remote Terraform plan/apply;
- no `project-identity/dev` live apply;
- no live GitHub Environment `ci` WIF test;
- no real PR workspace create/drop in Snowflake;
- no live dbt run against Snowflake;
- live effective grants are unverified;
- `PLATFORM_CONTROL` operational SQL deployment workflow has not run against real DEV;
- checkpoint, run ledger, freshness/reconciliation and SCD runtime semantics are source/static-CI proven only, not live-data proven;
- no UAT/PROD project deployment identities/workflows yet;
- no persisted cost views/resource monitors/budgets;
- no Health/Transport business marts/semantic models yet;
- Kafka Connector, direct Snowpipe Streaming and Openflow remain deferred.

## 24. Next useful work

Without live infrastructure, highest-value source work is now:

```text
1. add deterministic fixture tests for SCD2 replay/delete/reinsert/late-event behavior
2. integrate runtime ledger + check-result recording into a reusable pipeline execution wrapper
3. integrate canonical QUERY_TAG into live dbt invocation/model lifecycle
4. define deployment identity/workflow contract for DEV data projects, then UAT/PROD promotion
5. add recovery/backfill orchestration contract and pre-release clone/SWAP workflow skeleton
```

When real infrastructure becomes available:

```text
choose Azure Blob OR S3
-> provision state + cloud OIDC
-> organization bootstrap/import
-> identity/dev apply
-> platform/dev plan/apply/verify
-> run platform-control SQL deploy DEV + verify
-> project-identity/dev apply
-> configure project GitHub Environment ci
-> real PR workspace create/drop
-> live capture/checkpoint/SCD smoke tests
-> live dbt/basic-load smoke
-> UAT
-> protected PROD
```

Key ADRs now include:

```text
ADR-018  three-account topology
ADR-019  environment × domain database boundary
ADR-020  domain GUEST + workload warehouses
ADR-021  isolated ORGADMIN bootstrap
ADR-022  old S3-only choice — superseded
ADR-023  GitHub OIDC Terraform identity
ADR-024  Azure Blob/S3 backend adapters
ADR-025  DEV personal + PR CI workspace lifecycle
ADR-026  query-tag + cost-attribution contract
ADR-027  project PR-CI OIDC identity lifecycle
ADR-028  project/dataset/RAW metadata contracts
ADR-029  dbt physical target resolution
ADR-030  basic metadata-driven dbt load strategies
ADR-031  capture fidelity + reusable SCD consumers
ADR-032  PLATFORM_CONTROL native SQL lifecycle
```
