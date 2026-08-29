# Enterprise Snowflake Platform — Project Blueprint

> **Status:** Phase 1 source/static-CI foundation is implemented; live Snowflake/control-plane execution is still pending.
>
> **Authority:** Canonical long-term architecture for the Enterprise Snowflake Platform.
>
> **Fast handoff:** Read [`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) first for current SHAs, verified runs and immediate next actions.

## 1. Goal

Build a production-grade reusable Snowflake platform/reference implementation suitable for real enterprise adoption and Senior/Principal Data Engineering / Snowflake Platform Engineering work.

A new governed domain should onboard by declaring bounded technical metadata and writing its real business SQL, not by copying infrastructure, capture, SCD, deployment or observability mechanics.

## 2. Core principles

1. **Metadata drives stable technical behaviour.** Business joins, calculations, domain rules and genuinely different source semantics remain explicit code.
2. **Do not build a YAML programming language.** Metadata is a bounded contract, not an orchestration DSL.
3. **Git is desired-state/configuration source of truth.** `PLATFORM_CONTROL` stores mutable runtime/operational state.
4. **One object has one lifecycle owner.** Terraform, dbt, native SQL and runtime workflows must not fight over the same object.
5. **Promote immutable Git SHA.** Do not use DEV/UAT/PROD branches.
6. **Ingestion technology stops at the RAW contract.** Replacing Kafka/Openflow/Snowpipe Streaming must not force downstream redesign.
7. **Source fidelity is authoritative.** Downstream SCD cannot recreate source changes that capture already collapsed.
8. **Snowflake-native/classic execution is the reliability baseline.** Dynamic Tables are optional where appropriate, never the only implementation.
9. **Human and machine identities are separate.** Employee membership stays in enterprise identity systems.
10. **Least privilege before convenience.** Privilege expansion follows demonstrated requirements.
11. **Recovery, reconciliation, freshness, observability and cost attribution are design inputs.**
12. **Do not over-engineer ahead of a real consumer.** No placeholder directories or speculative abstractions.

## 3. Repository model

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

### Platform Infra

Owns Snowflake account/platform infrastructure, RBAC, warehouses, Terraform/WIF/state contracts, workspace/deployment permission boundaries, cost/governance foundations and the structural/native-SQL lifecycle of `PLATFORM_CONTROL`.

### Data Project Framework

Owns reusable technical mechanics: metadata contracts/validation, dbt package/macros/tests, environment/target resolution, workspace/query-tag helpers, capture/checkpoint/quality/SCD primitives and reusable PR/deployment workflows.

### Domain Projects

Health/Transport own RAW contracts, dataset configuration, source definitions, business SQL/tests, marts, semantic definitions and ingestion-specific configuration.

### Demo Source Systems

Represents deterministic systems outside Snowflake and stops at the project-owned RAW boundary.

## 4. Snowflake topology

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

CI is not a fourth account. PR CI runs in DEV with separate CI domain databases and compute. UAT remains a real account so account-scoped identity, RBAC, integrations and operations are proven before PROD.

Database boundary:

```text
<ENVIRONMENT>_<DOMAIN>
```

A database represents environment × governed data product/domain, not one physical source.

Stable schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Published schemas initially: `MARTS`, `SEMANTIC`. RAW source-purpose schemas appear only when a source is actually onboarded, for example `RAW_EHR_MSSQL`.

## 5. Human RBAC and employee identity

Per-domain human hierarchy:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

Stable database roles:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
  -> DR_<DOMAIN>_ANALYTICS_READ
  -> DR_<DOMAIN>_ANALYTICS_WRITE
  -> DR_<DOMAIN>_ANALYTICS_OWNER
```

Policy:

- GUEST reads published MARTS/SEMANTIC only and uses query compute.
- READER reads all stable domain layers.
- DEV DEVELOPER receives WRITE, personal-schema creation and transform compute.
- UAT/PROD DEVELOPER is read-only by default.
- UAT/PROD human roles receive no permanent transform warehouse grant in the baseline.
- Human emergency transform execution is JIT/break-glass through enterprise identity governance.
- Health authority never implies Transport authority and vice versa.

Terraform defines what roles/grants exist. Entra ID / Okta / SCIM or another approved identity system controls who receives them:

```text
Employee / contractor
  -> IdP group
  -> SCIM / approved provisioning
  -> AR_<DOMAIN>_<CAPABILITY>
```

Ordinary employee joins/leaves do not require Terraform changes.

## 6. Domain compute

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
WH_PLATFORM_OPS
```

Warehouses separate workload/concurrency/cost boundaries. Environment metadata declares project warehouse keys so new domains do not require copied Health/Transport grant blocks.

## 7. DEV personal and PR CI workspaces

Human roles attach to `DEV_<DOMAIN>`, never `CI_<DOMAIN>`.

Personal namespace:

```text
<DEVELOPER>_<LAYER>
```

DEV WRITE receives `CREATE SCHEMA` on the owning DEV database. This is a namespace convention, not strong per-person security isolation.

Machine-only PR CI:

```text
SU_GITHUB_<DOMAIN>_CI
  -> AR_<DOMAIN>_CI
      -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> WH_<DOMAIN>_CI
      -> EXECUTE TASK
```

PR schemas follow `PR_<NUMBER>_<LAYER>`, are transient/reproducible, and are guarded by strict cleanup-prefix validation. The CI workflow executes framework-generated workspace SQL only; it does not run untrusted PR business code while holding Snowflake credentials.

## 8. Stable project deployment identity

Stable DEV/UAT/PROD delivery uses a separate machine role:

```text
SU_GITHUB_<DOMAIN>_DEPLOY
  -> AR_<DOMAIN>_DEPLOY
      -> DR_<DOMAIN>_ANALYTICS_WRITE
      -> WH_<DOMAIN>_TRANSFORM
      -> CREATE STREAM
      -> CREATE TASK
      -> CREATE DYNAMIC TABLE
      -> EXECUTE TASK
```

The deployment role is outside the human hierarchy. It owns long-lived project runtime objects created by delivery so background Tasks/Dynamic Tables do not depend on a human role retaining runtime privileges.

No serverless `EXECUTE MANAGED TASK` is part of the baseline; named warehouses are used.

## 9. Terraform lifecycle and state

Terraform selectively owns stable platform infrastructure. It does not own dbt business models, employee membership, individual PR schemas or mutable pipeline progress.

Ten independent lifecycle/state roots:

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

Per-environment dependency:

```text
identity/<env>
  -> platform/<env>
      -> project-identity/<env>
```

`organization/` alone uses ORGADMIN. `identity/<env>` may use ACCOUNTADMIN only for machine-identity bootstrap. Routine `platform/<env>` uses only `AR_TERRAFORM_<ENV>`.

Current baseline:

```text
Terraform CLI                 1.16.0
Snowflake Terraform provider  2.19.0
```

Every root commits a provider lock file; CI validates all ten roots plus both backend profiles.

## 10. Terraform remote state

The platform is not AWS-dependent.

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

Terraform backend type is materialized at runtime with `terraform/scripts/select-backend.sh`. A deployment has one authoritative writable backend; Azure Blob and S3 are not simultaneous writable copies of the same state.

OneDrive/SharePoint may hold human-facing documents/evidence, not authoritative live Terraform state.

## 11. Platform and project workload identity

Platform Terraform:

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Project workload identities:

```text
DEV:  SU_GITHUB_<DOMAIN>_CI     -> AR_<DOMAIN>_CI
DEV:  SU_GITHUB_<DOMAIN>_DEPLOY -> AR_<DOMAIN>_DEPLOY
UAT:  SU_GITHUB_<DOMAIN>_DEPLOY -> AR_<DOMAIN>_DEPLOY
PROD: SU_GITHUB_<DOMAIN>_DEPLOY -> AR_<DOMAIN>_DEPLOY
```

All use GitHub OIDC + Snowflake Workload Identity Federation. Subjects are repository + GitHub Environment scoped. Snowflake audiences are account-scoped rather than the shared `snowflakecomputing.com` audience.

## 12. Immutable project delivery

Projects consume immutable framework revisions and upgrade deliberately.

Stable deployment requires:

```text
full 40-character project Git SHA
full 40-character framework Git SHA
```

The reusable framework deployment workflow:

1. accepts only `dev`, `uat` or `prod`;
2. verifies the project SHA belongs to `main` history;
3. checks out the exact project revision detached;
4. checks out the exact framework revision;
5. verifies the project's `dbt/packages.yml` pin matches that framework SHA;
6. enters the selected protected GitHub Environment;
7. reads environment-scoped Snowflake configuration after the environment is active;
8. requests an account-scoped OIDC token;
9. authenticates as `SU_GITHUB_<DOMAIN>_DEPLOY` / `AR_<DOMAIN>_DEPLOY`;
10. runs dbt against `<ENV>_<DOMAIN>` on `WH_<DOMAIN>_TRANSFORM`.

Promotion means:

```text
same reviewed project SHA
DEV -> UAT -> PROD
```

Environment branches are not used. Deployments to the same domain/environment are serialized with `cancel-in-progress: false`.

## 13. RAW contract and capture fidelity

Stable boundary:

```text
External source
  -> ingestion implementation
  -> project-owned RAW contract
  -> staging
  -> intermediate/canonical
  -> marts
  -> Semantic Views
```

Framework capture archetypes:

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

Bounded metadata may include checkpoint kind, deterministic ordering columns, idempotency columns and watermark lookback.

RAW preservation rules:

- full snapshots required for history/delete inference/replay are retained as immutable snapshot batches;
- full-change/full-event sources append immutable events to a regular Snowflake table before Stream consumers;
- Streams are delta/offset consumers, not the complete CDC history store;
- source fidelity limits downstream history guarantees.

See ADR-031 for capture archetypes and Dynamic Table fallback policy.

## 14. Metadata and dbt target model

Framework schema version 1 covers project, dataset and RAW contracts. Metadata includes bounded technical fields such as load strategy, implementation, business key, watermark, freshness, reconciliation and capture properties.

Business joins, formulas, free-form SQL and arbitrary workflow branching do not belong in metadata.

Physical target resolver inputs:

```text
project_code
environment = dev | ci | uat | prod
workload    = query | transform | ci
optional developer
optional PR number
```

Outputs include `DBT_DATABASE`, `DBT_WAREHOUSE`, `DBT_DEFAULT_SCHEMA` and the framework execution context. Model SQL uses `ref()` / `source()` rather than hard-coded environment databases.

Current dbt baseline:

```text
dbt-core      1.12.3
dbt-snowflake 1.12.0
```

Volatile framework release SHAs belong in `CURRENT_CONTEXT.md` and project pins, not in this long-term blueprint.

## 15. Runtime state, quality and observability

Git stores configuration; mutable progress belongs in account-local control state.

`PLATFORM_CONTROL.OPERATIONS` currently owns:

```text
PIPELINE_CHECKPOINT
PIPELINE_RUN
PIPELINE_CHECK_RESULT
ADVANCE_PIPELINE_CHECKPOINT(...)
```

Checkpoint state can represent watermark, cursor, LSN/source position, event offset, snapshot identity or file identity.

Framework quality/runtime primitives cover run start/finish, freshness checks, reconciliation metrics/comparison and structured check-result recording. Business-specific DQ remains explicit project tests.

Do not duplicate Snowflake-owned runtime state such as Stream offsets into custom control tables.

## 16. SCD architecture

Approved load strategies:

```text
full_refresh
append_only
incremental_merge
scd2_snapshot
scd2_merge
scd2_stream_task
```

Basic dbt-native configuration handles `full_refresh`, `append_only` and `incremental_merge`. Dedicated SCD macros handle SCD behavior.

SCD2 consumers follow capture fidelity:

- `scd2_snapshot` — transactional close/inferred-delete/insert at snapshot granularity;
- `scd2_merge` — correctness-first affected-key history rebuild from immutable ordered events;
- `scd2_stream_task` — append-only Stream + Triggered Task + transactional affected-key rebuild.

Canonical SCD2 target columns:

```text
_ESF_VALID_FROM
_ESF_VALID_TO
_ESF_IS_CURRENT
_ESF_VERSION_ORDINAL
```

Reusable invariants cover one-current-row, valid ranges, no overlap and deterministic unique version ordinal.

The framework includes a deterministic SQL behavioral oracle for duplicate replay, no-op state, update, delete/reinsert, late events and ordering ties. Static CI proves parse/render/discovery; live Snowflake execution remains pending.

See ADR-035 for SCD consumer semantics.

## 17. Dynamic Table policy

Dynamic Tables are optional execution/projection choices, not a required SCD2 mechanism.

Rules:

- every supported Dynamic Table path retains a classic regular-table alternative;
- production refresh mode is explicit; `AUTO` is not the framework default;
- window-heavy SCD2 Dynamic Tables require workload benchmarks;
- procedural MERGE/delete/orchestration remains on classic Snowflake primitives where that is clearer or more reliable.

## 18. Query tags and cost attribution

Required query-tag keys:

```text
project
environment
workload
```

Optional keys include source, pipeline, dataset, run ID, Git SHA, PR number and operation. No personal/secret/regulated/business payload data belongs in query tags.

Cost dimensions:

```text
storage/recovery             -> <ENVIRONMENT>_<DOMAIN>
compute                      -> WH_<DOMAIN>_<WORKLOAD>
query attribution            -> QUERY_TAG + QUERY_ATTRIBUTION_HISTORY
warehouse total/idle compute -> WAREHOUSE_METERING_HISTORY
serverless/ingestion         -> service-specific usage history
```

Do not create database-per-source merely for chargeback.

## 19. Recovery and promotion principles

Derived data recovery should prefer Snowflake-native Time Travel / zero-copy CLONE / controlled SWAP where appropriate. RAW evidence should not be blindly rolled back if it represents authoritative source history.

Recovery/backfill automation is not yet complete and remains a later implementation item after live DEV behavior is proven.

## 20. Current domain contracts

Health `patient`:

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
```

Transport `vehicle_position`:

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
```

Later direct Snowpipe Streaming and Kafka Connector paths must converge on the same Transport RAW contract.

## 21. What is proven vs not proven

Source/static CI proves structure, HCL/provider schemas, metadata validation, dbt parsing/rendering, reusable SQL contracts and workflow syntax/security assertions.

It does **not** prove:

- real remote-state access;
- real Snowflake account bootstrap/import;
- live WIF authentication;
- effective Snowflake grants;
- actual Stream/Task/Dynamic Table execution;
- concurrency/performance behavior;
- live SCD2 behavioral test execution;
- UAT/PROD promotion.

These remain part of the live verification gate.

## 22. Immediate execution order

```text
1. choose/provision authoritative remote state
2. bootstrap/import Snowflake accounts
3. bootstrap identity/dev
4. reviewed platform/dev plan/apply
5. verify DEV RBAC/warehouses/PLATFORM_CONTROL
6. bootstrap project-identity/dev
7. configure Health/Transport GitHub Environments ci + dev
8. prove real PR workspace create/drop
9. prove immutable main-history DEV deployment
10. execute live SCD2 behavioral oracle
11. repeat controlled pattern for UAT
12. repeat protected pattern for PROD
13. only then start streaming-ingestion comparison work
```

## 23. Deferred technologies

Until the live control-plane/framework foundation is proven, keep these deliberately deferred:

```text
Kafka Connector
Direct Snowpipe Streaming
Openflow
broad ingestion demos
full rollback/backfill automation
full observability dashboards
advanced governance policies
```

## 24. Key ADRs

- ADR-018 — three-account DEV/UAT/PROD topology.
- ADR-019 — environment × data-product database boundary.
- ADR-020 — domain GUEST access and workload warehouses; deployment compute portion amended by ADR-034.
- ADR-021 — isolated organization account bootstrap.
- ADR-023 — platform Terraform GitHub OIDC identity.
- ADR-024 — cloud-agnostic Terraform state backend profiles.
- ADR-025 — DEV personal and PR workspace lifecycle.
- ADR-026 — query-tag and cost-attribution contract.
- ADR-027 — DEV PR-CI OIDC identity lifecycle.
- ADR-028 — project metadata contracts.
- ADR-029 — dbt physical target resolution.
- ADR-030 — basic metadata-driven load strategies.
- ADR-031 — reusable capture archetypes and Dynamic Table fallback.
- ADR-032 — `PLATFORM_CONTROL` native SQL lifecycle.
- ADR-033 — Snowflake-native primitives before custom runtime.
- ADR-034 — project deployment identity and immutable promotion.
- ADR-035 — capture fidelity and reusable SCD consumers.
