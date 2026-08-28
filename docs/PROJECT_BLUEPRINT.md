# Enterprise Snowflake Platform — Project Blueprint

> **Status:** Phase 1 in progress — three-account Terraform foundation implemented in source; shared apply gated on remote state + workload identity
>
> **Authority:** Canonical architecture memory for the Enterprise Snowflake Platform. Update this file after each meaningful implementation/architecture step.
>
> **Canonical repository:** `enterprise-snowflake-platform-infra`

## 1. Project goals

Build a production-grade reusable Snowflake platform reference implementation credible for Senior/Principal Data Engineering and Snowflake Platform Engineering work and practical enough for a real organisation to adopt.

Key outcomes: clear ownership, repeatable onboarding, stable RAW contracts, metadata-driven technical behaviour, immutable Git SHA promotion, recoverability, reconciliation, freshness/SLOs, observability, cost attribution and multiple production patterns where workloads genuinely differ.

## 2. Non-goals

- Do not merge Metric Guard into this project.
- Do not maximise technology count for appearance.
- Do not force every ingestion/SCD2 workload into one implementation.
- Do not Terraform-manage every Snowflake object.
- Do not create a YAML programming language for business logic.
- Do not use DEV/UAT/PROD Git branches.
- Do not use Dynamic Tables for SCD2.
- Do not introduce Spark Streaming without a concrete need.
- Marketplace Secure Shares are not a core ingestion path.
- Do not build a custom ITSM platform.

## 3. Architecture principles

1. Convention over copy/paste.
2. Configuration for stable technical behaviour; code for genuine business differences.
3. Project autonomy inside platform guardrails.
4. Implementation diversity is acceptable; operational standards remain consistent.
5. RAW contracts isolate ingestion technology from downstream engineering.
6. Promote the same immutable Git SHA through environments.
7. Human production authority and machine deployment identity are separate.
8. Production readiness is defined by recoverability, not deployment success alone.
9. One object has one authoritative owner.
10. Git is configuration source of truth; `PLATFORM_CONTROL` stores runtime/operational state.
11. Prefer deterministic repair over manual PROD DML.
12. Account, database, schema and warehouse boundaries solve different problems; do not overload one boundary to solve all isolation/cost needs.

## 4. Repository architecture

| Repository | Responsibility |
|---|---|
| `enterprise-snowflake-platform-infra` | accounts/platform foundation, Terraform, central RBAC/governance/control plane/cost/recovery architecture |
| `enterprise-snowflake-data-project-framework` | versioned dbt/macros/tests/metadata/reusable delivery+recovery golden path |
| `enterprise-snowflake-demo-source-systems` | deterministic external source simulation only; stops at source/RAW boundary |
| `enterprise-snowflake-health-analytics` | Health contracts/config/business SQL/tests/semantic/ingestion config |
| `enterprise-snowflake-transport-analytics` | Transport contracts/config/business SQL/tests/semantic/streaming config |

Detailed target tree: [`architecture/REPOSITORY_LAYOUT.md`](architecture/REPOSITORY_LAYOUT.md).

## 5. Snowflake account/environment topology

Canonical topology is **three Snowflake accounts**:

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

DEV hosts personal/shared DEV and ephemeral PR CI. UAT is a separate production-like account specifically so account-scoped identities/RBAC/integrations/parameters/operational configuration can be tested before PROD. CI is not a fourth account.

See ADR-018 and [`architecture/ACCOUNT_TOPOLOGY.md`](architecture/ACCOUNT_TOPOLOGY.md).

## 6. Database / schema boundary

Analytics database pattern:

```text
<ENVIRONMENT>_<PROJECT>
```

A database represents **environment × data-product/domain**, not physical source system. Twenty MSSQL/MySQL/API sources do not imply twenty databases.

Stable transformation schemas inside project databases:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Source-purpose RAW schemas may be added when a real source is onboarded, for example `RAW_EHR_MSSQL` or `RAW_INSURANCE_API`; they are not pre-created speculatively.

Personal DEV schema pattern inside `DEV_<PROJECT>`:

```text
<DEVELOPER>_<LAYER>
```

PR CI schema pattern inside `CI_<PROJECT>`:

```text
PR_<NUMBER>_<LAYER>
```

See ADR-019 and `NAMING_CONVENTIONS.md`.

## 7. RBAC/access model

Capability account roles in each account:

```text
AR_PLATFORM_READER -> AR_PLATFORM_ENGINEER -> AR_PLATFORM_ADMIN
AR_<PROJECT>_READER -> AR_<PROJECT>_DEVELOPER -> AR_<PROJECT>_ADMIN
```

Database roles:

```text
DR_<PROJECT>_ANALYTICS_READ
  -> DR_<PROJECT>_ANALYTICS_WRITE
  -> DR_<PROJECT>_ANALYTICS_OWNER
```

Each analytics database maps to exactly one owning project. Terraform must not create project × database Cartesian-product roles.

Human developer WRITE policy:

- DEV: developer receives WRITE.
- UAT: developer read-only by default; deployment is machine identity.
- PROD: developer read-only by default; deployment is machine identity.

`ACCOUNTADMIN` remains restricted. Human employee lifecycle should come from enterprise SSO/IdP/SCIM rather than an employee list in Terraform.

## 8. Object ownership model

| Object/capability | Authoritative owner |
|---|---|
| Organization/account bootstrap | Platform Infra, separate privileged bootstrap |
| Project analytics databases | Terraform / Platform Infra |
| Stable structural schemas | Terraform / Platform Infra |
| Warehouses | Terraform / Platform Infra |
| Account roles/database roles/grants | Terraform / Platform Infra |
| WIF/workload identities/integrations | Terraform / Platform Infra |
| Cost controls/tags | Terraform/native platform ownership |
| `PLATFORM_CONTROL` structure | Terraform / Platform Infra |
| Shared procedures/tasks/alerts | controlled Snowflake SQL when clearer than Terraform |
| staging/intermediate/canonical/marts | data project via dbt |
| snapshots | data project via dbt |
| reusable technical macros/tests | Framework |
| project tests/semantic definitions | project + framework primitives |
| source simulator | Demo Source Systems |

No object is simultaneously authoritative in Terraform and dbt/ad-hoc SQL.

## 9. Terraform boundary

Terraform owns stable platform infrastructure/access objects. dbt owns transformation relations/snapshots/tests. Selected native operational procedures/tasks/alerts/recovery logic may use controlled SQL.

Current roots:

```text
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

Current modules:

```text
analytics-environment
warehouse
platform-control
rbac
```

Terraform CLI `1.16.0` and Snowflake provider `2.19.0` are pinned. Source credentials are not committed.

Snowflake provider supports `snowflake_account`, but account creation requires `ORGADMIN` plus initial admin material, so organization bootstrap is kept out of normal account stacks.

## 10. Data project framework design

Framework is a versioned dependency, not a forever-copied folder. It will provide dbt macros/tests, load/SCD2 strategies, reconciliation/freshness/audit contracts, metadata schemas/validation, reusable GitHub workflows and rollback/recovery/backfill templates.

Projects upgrade deliberately by release/tag/SHA.

## 11. Metadata-driven design principles

Metadata configures stable technical behaviour: strategy, keys/composite keys, source relation, timestamp/watermark, tracked columns, delete/dedup policy, quality/reconciliation/freshness thresholds, criticality and recovery targets.

Business joins/calculations/domain rules remain explicit SQL/code.

Escape hatch:

```yaml
implementation: custom
```

Custom implementations still participate in contracts/testing/observability/reconciliation/recovery/audit.

## 12. RAW contracts

Project-owned RAW contracts define the boundary between ingestion and downstream engineering: source/owner/schema version/entity/grain/key/columns/types/nullability/source timestamp/CDC semantics/sequence/cadence/retention/classification/breaking-change policy.

Typical technical fields:

```text
source_operation
source_sequence
source_updated_at
ingested_at
batch_id
source_system
```

## 13. Ingestion patterns

All ingestion implementations converge on project RAW contracts:

```text
Synthetic/file/database source ─┐
Snowpipe Streaming             ─┼─> RAW -> downstream dbt
Kafka Connector                ─┤
Openflow CDC                   ─┘
```

Transport later compares direct Snowpipe Streaming with Kafka -> Snowflake Kafka Connector -> Snowpipe Streaming using the same logical event contract. Normally one path is active.

Health adds Openflow only after downstream Health is already proven.

## 14. dbt architecture

```text
RAW -> staging -> intermediate/canonical -> marts -> semantic
```

Use `source()`, `ref()`, tests, source freshness, snapshots where appropriate, framework dependencies and environment-aware database/schema resolution. Model SQL never hard-codes DEV/UAT/PROD physical database names.

## 15. SCD2 strategy catalog

Dynamic Tables are excluded for SCD2.

Approved patterns:

1. `scd2_snapshot` — dbt Snapshot
2. `scd2_merge` — explicit incremental/MERGE
3. `scd2_stream_task` — Snowflake Streams + Tasks

Tests cover initial/unchanged/changed records, composite keys, multiple changes, duplicates, late/out-of-order data, deletes, idempotency, backfill, partial failure and deterministic history rebuild.

## 16. CI/CD lifecycle

```text
feature branch
-> personal/shared DEV (DEV account)
-> PR CI (CI_<PROJECT> in DEV account)
-> review + merge
-> UAT account
-> approval
-> PROD account
-> smoke/regression/reconciliation
```

PR close removes ephemeral CI resources. CI/CD and operational scheduling remain separate concerns.

## 17. Release promotion

One Git history per project; no environment branches. Promote the exact same immutable `git_sha` through DEV -> CI -> UAT -> PROD. Release/deployment history goes to account-local `PLATFORM_CONTROL.DEPLOYMENT` with cross-account reporting added separately if useful.

## 18. Production rollback

For derived data:

```text
pre-release zero-copy clone
-> deploy
-> smoke + DQ + reconciliation
-> PASS: retain release
-> FAIL: controlled SWAP to known-good state
-> validate/reconcile/resume
```

Do not blindly roll back RAW. Correct Git desired state after runtime rollback.

## 19. Data repair/recovery

Support bounded retry, checkpoint/watermark, replay, idempotent rerun, backfill, Time Travel, UNDROP, point-in-time/zero-copy clone recovery, affected-window rebuild and deterministic SCD2 history rebuild. Prefer these over manual PROD DML.

## 20. Data quality

Baseline: not-null, uniqueness, relationships, accepted values, domain assertions, volume checks, SCD2 invariants, schema contracts and reconciliation. dbt tests alone are not full production reconciliation.

## 21. Reconciliation

Support row count, distinct keys, control totals, min/max business timestamp, watermarks, rejected rows and duplicates across boundaries. Results go to `PLATFORM_CONTROL.QUALITY.RECONCILIATION_RESULTS` once the first consumer is implemented.

## 22. Freshness

Track separately:

1. source freshness;
2. pipeline freshness / processed watermark;
3. published dataset freshness.

Pipeline success does not imply consumer readiness.

## 23. SLI / SLO / SLA

- SLI = measured signal.
- SLO = internal reliability objective.
- SLA = optional formal/business commitment.

Dataset readiness may require transformation, DQ, reconciliation, freshness and semantic regression all to pass.

## 24. Observability

Start Snowflake-native: account usage, query/warehouse history, dbt artifacts, GitHub Actions and `PLATFORM_CONTROL`.

Monitor freshness, pipelines/tasks, long-running work, dbt failures, DQ/reconciliation, publish readiness, warehouse/query usage, deployments/rollback/recovery, SLO breaches, cost anomalies and orphaned CI resources.

## 25. Incident management

```text
DETECT -> TRIAGE -> CONTAIN -> RECOVER -> RECONCILE -> VALIDATE -> RESUME -> CLOSE
```

Use practical incident records/alerts/runbooks; do not build a custom ITSM system.

## 26. Cost attribution / recovery

Do not use database-per-source as the primary cost model.

Use complementary boundaries:

```text
Project storage/recovery       -> project database (DEV_HEALTH, PROD_TRANSPORT, ...)
Source/table storage detail    -> schema/table storage metrics
Compute                        -> project/workload warehouse + query tags
Serverless ingestion/services  -> Snowflake service usage history
```

Query tags should eventually carry metadata such as project/source/pipeline/dataset/run/release so compute can be attributed below warehouse level.

Warehouses remain workload-appropriate, conservative by default (`XSMALL`, auto-suspend, initially suspended, explicit timeout). Cost monitors/budgets/tags are later Phase 1 hardening.

## 27. Semantic Views

Use Snowflake-native Semantic Views; Cube is excluded. Semantic definitions participate in project release/regression lifecycle where practical.

## 28. Project onboarding

A future Finance project should primarily add project metadata, RAW contracts/source mappings/domain SQL/tests/semantic definitions and source-specific ingestion config.

Platform onboarding would derive databases such as:

```text
DEV_FINANCE
CI_FINANCE
UAT_FINANCE
PROD_FINANCE
```

Adding another physical Finance source normally adds source metadata/RAW structures, not another environment database.

Projects do not reimplement generic CI/CD, SCD2, reconciliation, freshness, audit, recovery or Terraform modules.

## 29. Implementation roadmap

- **Phase 0 — Architecture:** complete.
- **Phase 1 — Platform Foundation:** **in progress**; three-account Terraform code/baseline implemented, state/auth/apply/cost bootstrap pending.
- **Phase 2 — Framework Foundation:** metadata validation, dbt package, environment macros, basic loads, reusable CI, operational logging.
- **Phase 3 — Thin CI/CD spine:** prove DEV -> PR CI -> UAT -> PROD with exact SHA, history/recovery point/cleanup/rollback skeleton.
- **Phase 4 — Health vertical slice:** deterministic Health RAW -> semantic with contracts/DQ/reconciliation/freshness/recovery/SCD2.
- **Phase 5 — Transport streaming:** direct Snowpipe Streaming then Kafka Connector, same RAW event contract.
- **Phase 6 — Complete pattern catalog:** all approved load/SCD2 patterns, late data/dedup/replay/backfill/schema evolution.
- **Phase 7 — Production hardening:** masking/RAP/classification/cost/drift/health views/alerts/recovery drills/SLO reporting.
- **Phase 8 — Openflow:** SQL Server -> Openflow CDC -> Health RAW without downstream redesign.

## 30. ADR index / current status

Key accepted ADRs:

| ADR | Decision | Status |
|---|---|---|
| ADR-001 | five repository architecture | Accepted |
| ADR-002 | two-account topology | **Superseded by ADR-018** |
| ADR-003 | capability account roles + database roles | Accepted |
| ADR-004 | selective Terraform / one owner | Accepted |
| ADR-006 | metadata technical behaviour, code business logic | Accepted |
| ADR-007 | RAW contract boundary | Accepted |
| ADR-016 | project-qualified schemas in shared databases | **Superseded by ADR-019** |
| ADR-017 | shared apply requires remote state + workload identity | Accepted |
| ADR-018 | three-account DEV/UAT/PROD topology | Accepted |
| ADR-019 | environment × data-product database boundary | Accepted |

### Phase 1 completed in source control

- [x] Terraform CLI `1.16.0` and provider `2.19.0` pinned.
- [x] `config/environments/{dev,uat,prod}.yml` implemented.
- [x] old `nonprod` configuration/root stack removed.
- [x] `analytics-environment`, `warehouse`, `platform-control`, `rbac` modules implemented.
- [x] DEV root: `DEV_HEALTH`, `CI_HEALTH`, `DEV_TRANSPORT`, `CI_TRANSPORT`.
- [x] UAT root: `UAT_HEALTH`, `UAT_TRANSPORT`.
- [x] PROD root: `PROD_HEALTH`, `PROD_TRANSPORT`.
- [x] account-local `PLATFORM_CONTROL` structural schemas.
- [x] project-aware RBAC avoids cross-project database-role Cartesian products.
- [x] DEV human developers WRITE; UAT/PROD developers read-only by default.
- [x] warehouse cost/isolation baseline.
- [x] credential-free Terraform CI matrix now targets DEV/UAT/PROD.
- [x] three-account/database/naming/RBAC docs aligned.
- [x] Kafka, Snowpipe Streaming, Openflow and broad dbt still intentionally deferred.

Still required before Phase 1 exit:

- [ ] obtain a successful GitHub-hosted/local Terraform init and commit `.terraform.lock.hcl` per root as appropriate;
- [ ] choose durable independent remote state for DEV/UAT/PROD;
- [ ] implement WIF/OIDC and dedicated machine roles;
- [ ] implement/execute narrowly privileged Organization account bootstrap or import existing DEV/UAT/PROD accounts;
- [ ] review/apply DEV plan first and verify Snowflake objects/grants;
- [ ] prove UAT plan/apply after DEV; keep PROD disabled until both are sound;
- [ ] implement personal DEV/PR CI schema lifecycle outside long-lived Terraform state;
- [ ] add cost-control/resource-monitor/tagging baseline where administrative/edition boundaries permit.

## 31. Next implementation step

Continue Phase 1 in this order:

1. get Terraform `fmt/init/validate` actually executing (current GitHub runner issue must be resolved/verified);
2. generate provider lock files;
3. select/record remote-state backend with three independent state boundaries;
4. implement GitHub-to-Snowflake WIF and least-privilege machine roles;
5. implement organization-account bootstrap/import workflow for DEV/UAT/PROD without embedding high-privilege secrets;
6. produce DEV plan-only CI, review and apply DEV;
7. verify role/database/schema/warehouse topology and cost tagging/query-tag conventions;
8. only then enable UAT, and later protected PROD planning/apply.

Do **not** start Kafka, Snowpipe Streaming, Openflow or broad dbt modelling during this step.
