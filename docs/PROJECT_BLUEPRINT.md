# Enterprise Snowflake Platform — Hybrid Framework v2 Blueprint

> **Status:** Canonical long-term architecture.
>
> **Implementation boundary:** source/static implementation is substantially complete; live DEV/WIF/Snowflake acceptance remains pending and is tracked in platform issue #6.
>
> **Fast handoff:** read `docs/CURRENT_CONTEXT.md` first for current SHAs, verified CI and blockers.

## 1. Goal

Build a production-grade Snowflake reference platform that can onboard governed domains without copying infrastructure or hiding business logic behind a large metadata DSL.

The governing rule is:

```text
Metadata = HOW TO RUN
SQL      = WHAT THE DATA MEANS
```

A new domain declares bounded technical metadata, writes readable domain SQL and consumes reusable platform/framework mechanics through immutable dependencies.

## 2. Core principles

1. **Business meaning stays in SQL.** Joins, filters, CASE expressions, aggregations, business-effective rules and domain calculations remain readable project code.
2. **Metadata is bounded technical configuration.** It must not become a second programming language.
3. **Source acquisition and downstream processing have different owners.** External source/connector state ends at landed Bronze evidence; Framework processing begins after data is in Snowflake.
4. **Git is configuration truth.** `PLATFORM_CONTROL` stores runtime/audit state, not editable desired configuration.
5. **One object has one lifecycle owner.** Terraform, native SQL, dbt and runtime workflows must not fight over the same object.
6. **Promote immutable Git SHA.** DEV/UAT/PROD branches are not used.
7. **Source fidelity limits downstream guarantees.** SCD cannot recreate changes the source/ingestion path never preserved.
8. **Snowflake-native services are preferred when they own the required state.** Do not mirror Stream offsets, Task history or other Snowflake-owned runtime state into custom ledgers.
9. **Human and machine identities are separate.** Terraform defines roles; enterprise identity systems assign people.
10. **Least privilege precedes convenience.** Domain runtime and recovery access is server-fixed and domain-scoped.
11. **Recovery, observability, reconciliation and cost attribution are design inputs.**
12. **Do not over-engineer before a real consumer exists.** Add reusable abstractions only when a repeated technical behavior is proven.

## 3. Five-repository model

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

### Platform Infra

Owns Snowflake organization/account/platform infrastructure, RBAC, warehouses, Terraform/WIF/state contracts, project identity, protected deployment boundaries, cost/governance foundations and structural/native-SQL lifecycle of `PLATFORM_CONTROL`.

### Data Project Framework

Owns schema-v2 metadata validation, config snapshot rendering, small dbt utilities, justified stateful SCD materializations, quality/control helpers and reusable project PR/deployment workflows.

The Framework does **not** own SQL Server LSNs, Kafka source offsets, API cursors, connector scheduling or source extraction mechanics.

### Domain Projects

Health/Transport own source contracts, dataset execution metadata, dbt source definitions, readable Silver/Gold SQL, domain tests, semantic/business logic and explicit domain recovery plans.

Each domain also keeps a small framework-independent `standalone/` contract/portability fixture.

### Demo Source Systems

Represents deterministic systems outside Snowflake. It is the future home for external integration/source runtime such as SQL/file/event generators, Kafka producers and streaming comparisons. It is deliberately separate from the small domain portability fixtures.

## 4. Three-account Snowflake topology

```text
Snowflake Organization
├── DEV account
│   ├── DEV_HEALTH
│   ├── CI_HEALTH
│   ├── DEV_TRANSPORT
│   ├── CI_TRANSPORT
│   └── PLATFORM_CONTROL
├── UAT account
│   ├── UAT_HEALTH
│   ├── UAT_TRANSPORT
│   └── PLATFORM_CONTROL
└── PROD account
    ├── PROD_HEALTH
    ├── PROD_TRANSPORT
    └── PLATFORM_CONTROL
```

CI is not a fourth account. PR CI runs in DEV using isolated CI databases/compute. UAT remains a separate account so account-scoped identity, integrations, RBAC and operations are proven before PROD.

A stable domain database represents:

```text
environment × governed domain/data product
```

It does not represent one connector or physical source.

## 5. Medallion data plane

Stable domain schemas are:

```text
BRONZE
SILVER_STAGING
SILVER_INTERMEDIATE
SILVER_CANONICAL
GOLD_MARTS
GOLD_SEMANTIC
DQ
```

Responsibilities:

```text
BRONZE
  source-faithful landed evidence

SILVER_STAGING
  readable typing, naming, basic dedupe/normalization

SILVER_INTERMEDIATE
  optional technical shaping

SILVER_CANONICAL
  authoritative current state / history correctness

GOLD_MARTS
  business joins, KPIs, aggregates, reporting entities

GOLD_SEMANTIC
  semantic preparation / published semantic layer
```

Silver is the **data-correctness layer**. Gold is the **business-derivation layer**.

Ordinary new sources coexist in a domain `BRONZE` schema. Source identity belongs in contracts/object naming/metadata; a source-specific schema is a governance exception, not the default connector boundary.

## 6. Ingestion and source-contract boundary

```text
External source
  -> source/connector implementation
  -> BRONZE landed evidence
──────────────────────────────── Framework processing boundary
  -> Silver
  -> Gold
```

Source/connector runtime may own:

```text
SQL Server LSN / CDC position
Kafka partition + offset
API cursor
file identity
source-side watermark
connector retries/scheduling
snapshot-to-incremental extraction handoff
```

Those are not Framework processing checkpoints.

The project raw/source contract v2 describes the evidence downstream is allowed to assume:

```text
source system / entity / grain
business key
column contract/classification
source timestamp where applicable
change semantics: snapshot | append | cdc
operation/sequence/delete semantics where applicable
capture_fidelity
ordering_columns
idempotency_key
cadence / retention / breaking-change policy
```

It does not describe connector implementation state.

## 7. Dataset metadata v2

Dataset policy is table/dataset-scoped and uses three independent axes:

```text
load.strategy
materialization.type
runtime.mode
```

Supported standard load strategies:

```text
full_refresh
append_only
incremental_merge
scd1
scd2
custom
```

Materialization and runtime remain independent. Names such as `scd2_merge`, `scd2_snapshot` and `scd2_stream_task` do not exist in v2.

A single domain database can therefore mix full refresh, append-only, incremental merge, SCD1, SCD2, Dynamic Tables and explicit custom behavior without creating a database per refresh policy.

Logical compute is declared as a workload such as:

```text
compute.workload: transform
```

Platform environment metadata resolves `(domain, environment, workload)` to a physical warehouse.

## 8. SCD correctness

### SCD1

Framework SCD1 is a bounded current-state primitive:

- keyed merge/upsert;
- deterministic domain SQL supplies the desired current row;
- tombstone delete mechanics are supported when declared by the raw contract;
- business/source ordering logic remains readable in the domain model.

Health `patient` is the current reference SCD1 consumer.

### SCD2

Framework SCD2 publishes one authoritative history table and a normal current view.

Required semantics include:

```text
deterministic business-key ordering
replay/idempotency safety
no-op state suppression
tombstone delete
reinsert after delete
late-arriving event correction
valid_from
valid_to
is_current
version_order
```

The standard implementation retains a technical landed-event sidecar ledger and rebuilds only affected business keys from complete retained evidence. Gold consumers read `<entity>_current`; they do not repeat `where is_current = true`.

Transport `vehicle_status` is the reference SCD2 consumer.

Dynamic Tables are not the default stateful SCD2 implementation.

## 9. Dynamic Table policy

Dynamic Tables are an execution/materialization option, primarily for declarative Gold derivations when Snowflake can own refresh scheduling.

Rules:

- Dynamic Table is not a load strategy;
- Gold-first is the default posture;
- `ADAPTIVE` refresh is preferred where appropriate;
- stateful SCD history stays on the dedicated correctness path unless live evidence justifies another implementation;
- named warehouses remain the baseline rather than serverless managed-task assumptions.

Transport `depot_fleet_status` is the reference Gold Dynamic Table.

## 10. Human RBAC

Per-domain human hierarchy:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

Stable database roles provide guest/read/write/owner capabilities. Employees/contractors receive account roles through an approved identity provider/SCIM process; ordinary join/leave events do not require Terraform changes.

Health authority never implies Transport authority.

UAT/PROD human roles do not receive permanent routine transform capability in the baseline; emergency execution is JIT/break-glass.

## 11. Machine identities and workloads

Workload warehouses follow domain + workload naming within each account:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
WH_PLATFORM_OPS
```

DEV PR CI:

```text
SU_GITHUB_<DOMAIN>_CI
  -> AR_<DOMAIN>_CI
```

Stable delivery:

```text
SU_GITHUB_<DOMAIN>_DEPLOY
  -> AR_<DOMAIN>_DEPLOY
```

Recovery:

```text
AR_<DOMAIN>_RECOVERY
```

Recovery is separate from normal development/deploy. It receives domain read visibility, transform warehouse usage and TRUNCATE on current/future domain tables, but no broad cross-domain or shared-control DML.

All GitHub machine identities use Snowflake Workload Identity Federation with GitHub Environment/repository-scoped subjects and account-scoped audiences.

## 12. DEV personal and PR workspaces

Humans use the stable DEV domain database, not the CI database. Personal namespaces are conventions for developer isolation.

PR CI uses transient reproducible schemas under the CI database:

```text
PR_<NUMBER>_<LAYER>
```

Reusable Framework workflows create/drop only validated prefixed workspaces. Full stable-domain processing reset explicitly rejects a non-empty `ESF_SCHEMA_PREFIX` so a PR/personal workspace cannot target stable reset relations.

## 13. Terraform lifecycle and remote state

Terraform owns stable platform infrastructure, not dbt business models, employee membership, PR schemas or mutable pipeline progress.

Independent lifecycle/state roots:

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

Dependency per environment:

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

One deployment has one authoritative writable backend. OneDrive/SharePoint may store human evidence/documents, never authoritative live Terraform state.

## 14. `PLATFORM_CONTROL`

`PLATFORM_CONTROL` is account-local control/audit state, separate from the domain data plane.

Current families include:

```text
CONFIG
  DATASET_CONFIG_SNAPSHOT

OPERATIONS
  PIPELINE_CHECKPOINT
  PIPELINE_RUN
  PIPELINE_CHECK_RESULT
  PIPELINE_BOOTSTRAP
  DATASET_LIFECYCLE
  DATASET_RESET
```

Domain runtime/recovery access uses generated server-fixed views/procedures such as:

```text
<DOMAIN>_PIPELINE_CHECKPOINT
<DOMAIN>_PIPELINE_RUN_START(...)
<DOMAIN>_ADVANCE_PIPELINE_CHECKPOINT(...)
<DOMAIN>_PIPELINE_BOOTSTRAP_*(...)
<DOMAIN>_DATASET_RESET_*(...)
<DOMAIN>_REGISTER_DATASET_CONFIG_SNAPSHOT(...)
```

Project/environment are fixed by the generated API; callers cannot select another domain by passing `PROJECT_CODE`.

The ordered deployment bundle is rendered from `config/environments/<env>.yml` and contains base state plus all generated domain surfaces.

## 15. Processing checkpoints vs source checkpoints

Framework/`PLATFORM_CONTROL` checkpoints describe **already-landed Snowflake processing state** only.

Examples may include a landed-data watermark, snapshot identifier, event offset or file identity when the downstream processor itself owns that boundary.

Do not mirror:

- Snowflake Stream offsets;
- source connector LSNs/cursors already owned by ingestion;
- Kafka connector offsets already owned by the connector;
- Snowflake Task run history.

## 16. Bootstrap/handoff

The Framework/Platform bootstrap lifecycle is for the boundary between **already-landed Bronze evidence** and downstream processing, not for executing source extraction.

It can record/guard a processing handoff only after ingestion has produced a consistent landed boundary. Source-specific snapshot/CDC consistency mechanics remain ingestion-owned.

Bootstrap metadata is therefore not part of the raw/source contract v2.

## 17. Generation-aware processing reset

Full reset is a downstream processing lifecycle, not an automatic source purge.

State machine:

```text
ACTIVE generation N
 -> RESETTING
 -> explicit domain-owned reconstructable-table cleanup
 -> generation N+1 / READY_FOR_INITIAL_LOAD
 -> normal successful reload/checkpoint
 -> ACTIVE
```

The reset ledger moves:

```text
RESETTING -> READY_FOR_RELOAD -> COMPLETED
```

Old-generation run/checkpoint/bootstrap/check history is retained for audit.

Current domain reset policy deliberately preserves ingestion-owned Bronze evidence:

Transport:

```text
truncate SILVER_CANONICAL.VEHICLE_STATUS_HISTORY
truncate SILVER_CANONICAL.VEHICLE_STATUS_HISTORY__ESF_EVENTS
```

Health:

```text
truncate SILVER_CANONICAL.PATIENT
```

If Bronze evidence itself is corrupt/missing, source/ingestion recovery is a separate operation.

## 18. Configuration snapshots

Git remains configuration truth. After successful deployment, validated dataset/source technical metadata can be registered as immutable config snapshots through domain-scoped config procedures.

The snapshot table is audit state, not an editable runtime parameter store. Re-registering identical content is idempotent; conflicting content for the same identity fails closed.

## 19. Quality, reconciliation and observability

Prefer Snowflake-native monitoring/runtime history when Snowflake already owns the execution.

Framework/platform reuse is appropriate for:

- bounded freshness/reconciliation contracts;
- project-run observability when the authoritative orchestrator is outside Snowflake;
- config/deployment audit;
- query tags and cost attribution;
- domain-specific checks that Snowflake native Data Quality Monitoring does not represent directly.

Business-specific DQ remains explicit project SQL/tests.

Query tags must use technical identifiers only; never put secrets, personal data or regulated payloads in them.

## 20. Immutable project delivery

Projects consume immutable full Framework commit SHAs.

Stable deployment requires:

```text
full project Git SHA reachable from main
full Framework Git SHA matching dbt package pin
selected protected GitHub Environment
account-scoped Snowflake WIF
```

Promotion means:

```text
same reviewed project SHA
DEV -> UAT -> PROD
```

Do not rebuild a different code revision between environments. The exact promotion orchestrator is intentionally implemented only after the DEV path is live-proven.

## 21. Portability boundary

Transport and Health contain standalone synthetic source/contract fixtures that run without:

```text
Framework
PLATFORM_CONTROL
Terraform
enterprise WIF
enterprise database/warehouse naming
```

These prove domain portability and source-contract behavior. They are not a replacement for the external integration/source runtime in `enterprise-snowflake-demo-source-systems`.

## 22. What v2 intentionally removed

Do not reintroduce:

```text
schema v1 compatibility/normalization
load_strategy
scd1_merge
scd2_merge
scd2_snapshot
scd2_stream_task
connector checkpoint metadata in raw contracts
Framework-owned source LSN/Kafka/API cursor state
YAML business-SQL DSLs
one database per physical source
one control table per source
broad project DML on shared PLATFORM_CONTROL tables
```

Historical ADRs may retain those names only when explicitly marked superseded/replaced.

## 23. Current proof boundary

Source/static CI currently proves:

- Terraform topology/RBAC/state contracts;
- metadata v2 validation;
- offline dbt parse/materialization routing;
- SCD2 behavioral oracle;
- standalone domain portability fixtures;
- deterministic Platform Control renderers;
- domain-scoped operational/bootstrap/reset/config SQL shape;
- ordered control-plane deployment bundle shape;
- generation/reset safety contracts.

It does **not** prove:

```text
real Snowflake WIF
grant/owner-rights behavior in a live account
PR workspace create/drop
live SCD1/SCD2 correctness
live Dynamic Table refresh
live reset/generation rollover
cross-domain denial
real source ingestion/CDC consistency
performance/concurrency/cost behavior
same-SHA DEV->UAT->PROD promotion
```

Those live gates are tracked in platform issue #6. Repository protection/rulesets are tracked in issue #5.

## 24. Implementation order from here

```text
1. configure protected DEV GitHub Environment + Snowflake WIF
2. apply/verify DEV identity + platform + project-identity Terraform
3. deploy the complete PLATFORM_CONTROL bundle
4. prove domain isolation and PR workspace lifecycle
5. deploy Transport/Health and run live SCD/Dynamic Table scenarios
6. prove generation-aware processing reset
7. run framework-free standalone live proofs
8. introduce a real external demo source/ingestion path
9. only then encode exact same-SHA UAT/PROD promotion
10. expand reusable patterns only when a real consumer proves the need
```
