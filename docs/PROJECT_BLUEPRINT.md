# Enterprise Snowflake Platform — Project Blueprint

> **Status:** Phase 0 complete — ready for Phase 1 Platform Foundation
>
> **Authority:** This is the canonical architecture memory for the Enterprise Snowflake Platform project. After each meaningful implementation step, update architecture decisions, implementation status, and the next implementation step here.
>
> **Canonical repository:** `enterprise-snowflake-platform-infra`

## 1. Project goals

Build a production-grade, reusable Snowflake platform reference implementation credible for Senior/Principal Data Engineering and Snowflake Platform Engineering work and practical enough for a real organisation to adopt.

Key outcomes: clear ownership boundaries, repeatable onboarding, stable RAW contracts, metadata-driven technical behaviour, immutable Git SHA promotion, recoverability, reconciliation, freshness/SLOs, observability, cost controls, and multiple production patterns where workloads genuinely differ.

## 2. Non-goals

- Do not merge Metric Guard into this project.
- Do not maximise technology count for appearance.
- Do not force all ingestion or SCD2 workloads into one implementation.
- Do not Terraform-manage every Snowflake object.
- Do not create a YAML programming language for business logic.
- Do not use separate DEV/UAT/PROD code branches.
- Do not use Dynamic Tables for SCD2.
- Do not introduce Spark Streaming without a concrete requirement.
- Marketplace Secure Shares are not a core ingestion path.
- Do not build a full ITSM product.

## 3. Architecture principles

1. **Convention over copy/paste.**
2. **Configuration for stable technical behaviour; code for genuine business differences.**
3. **Project autonomy inside platform guardrails.**
4. **Implementation diversity is acceptable; operational standards remain consistent.**
5. **RAW contracts isolate ingestion technology from downstream engineering.**
6. **Promote the same immutable Git SHA through environments.**
7. **Human production authority and machine deployment identity are separate.**
8. **Production readiness is defined by recoverability, not deployment success alone.**
9. **One object has one authoritative owner.**
10. **Git is configuration source of truth; `PLATFORM_CONTROL` stores runtime/operational state.**
11. **Prefer deterministic repair over manual production DML.**
12. **Do not introduce technology without a real requirement.**

## 4. Repository architecture

Canonical repositories:

| Repository | Owner | Responsibility |
|---|---|---|
| `enterprise-snowflake-platform-infra` | Platform Engineering | Snowflake foundation, Terraform, central RBAC, governance, control plane, cost controls, observability/recovery architecture and canonical documentation |
| `enterprise-snowflake-data-project-framework` | Platform Engineering | Versioned reusable golden path: dbt package, load/SCD2 patterns, metadata schemas, tests, CI/CD/recovery workflows |
| `enterprise-snowflake-demo-source-systems` | Demo/test tooling | Deterministic source simulation only; stops at source/RAW boundary |
| `enterprise-snowflake-health-analytics` | Health data project | Health contracts/config, business SQL/tests/semantic definitions, project ingestion config |
| `enterprise-snowflake-transport-analytics` | Transport data project | Transport contracts/config, business SQL/tests/semantic definitions, project streaming config |

### Initial skeletons

```text
enterprise-snowflake-platform-infra/
├── README.md
├── docs/{PROJECT_BLUEPRINT.md,architecture/,adr/,standards/,runbooks/}
├── terraform/{modules/,stacks/{nonprod,prod}/}
├── snowflake/{bootstrap,control,governance,monitoring,alerts,recovery}/
├── config/{projects,access-profiles,governance}/
├── observability/
└── .github/workflows/

enterprise-snowflake-data-project-framework/
├── README.md
├── dbt_package/{macros/,tests/}
├── project_schema/{project.schema.json,dataset.schema.json}
├── workflows/
├── bootstrap/
├── docs/{patterns,operations}/
└── examples/

enterprise-snowflake-demo-source-systems/
├── README.md
├── pyproject.toml
├── sources/{health,transport}/
├── adapters/{rest,sse,gtfs_realtime}/
├── sinks/{snowflake_direct,snowpipe_streaming,kafka,sql_server}/
├── scenarios/
└── tests/

enterprise-snowflake-health-analytics/
├── README.md
├── config/{project.yml,datasets/,contracts/raw/,operations/}
├── dbt/{models/,snapshots/,tests/}
├── ingestion/openflow/
└── .github/workflows/

enterprise-snowflake-transport-analytics/
├── README.md
├── config/{project.yml,datasets/,contracts/raw/,operations/}
├── dbt/{models/,snapshots/,tests/}
├── ingestion/{snowpipe_streaming,kafka}/
└── .github/workflows/
```

Directories are created only when they gain real content; empty placeholders are not evidence of implementation.

## 5. Snowflake account/environment topology

Use a Snowflake Organization with two accounts:

```text
NONPROD
├── ANALYTICS_DEV
├── ANALYTICS_CI
└── ANALYTICS_UAT

PROD
└── ANALYTICS_PROD
```

`ANALYTICS_DEV` supports personal and shared DEV schemas. `ANALYTICS_CI` supports ephemeral PR schemas. UAT/PROD use stable release schemas. Physical environment names are configuration-driven; dbt model SQL never hard-codes DEV/UAT/PROD database names.

## 6. RBAC/access model

Capability-based account roles:

```text
AR_PLATFORM_READER
AR_PLATFORM_ENGINEER
AR_PLATFORM_ADMIN

AR_<PROJECT>_READER
AR_<PROJECT>_DEVELOPER
AR_<PROJECT>_ADMIN
```

Examples: `AR_HEALTH_DEVELOPER`, `AR_TRANSPORT_ADMIN`.

`AR_PLATFORM_ADMIN` is not synonymous with `ACCOUNTADMIN`; `ACCOUNTADMIN` stays highly restricted. Platform and project capabilities are independent and may be combined where responsibilities require it.

Database roles represent object access:

```text
DR_<PROJECT>_ANALYTICS_READ
DR_<PROJECT>_ANALYTICS_WRITE
DR_<PROJECT>_ANALYTICS_OWNER
```

Account roles inherit the appropriate database roles.

## 7. Object ownership model

| Object/capability | Authoritative owner | Mechanism |
|---|---|---|
| Organisation/account foundation | Platform Infra | Terraform/manual bootstrap where required |
| Analytics databases | Platform Infra | Terraform |
| Platform/control schemas | Platform Infra | Terraform / controlled SQL |
| Warehouses | Platform Infra | Terraform |
| Account roles | Platform Infra | Terraform |
| Database roles/grants | Platform Infra | Terraform |
| OIDC/workload identities/integrations | Platform Infra | Terraform |
| Resource monitors/budgets/cost controls | Platform Infra | Terraform / Snowflake native |
| `PLATFORM_CONTROL` structure | Platform Infra | Terraform / controlled SQL |
| Shared procedures/tasks/alerts | Platform Infra | controlled Snowflake SQL unless Terraform is explicitly selected |
| staging/intermediate/canonical/marts | Data project | dbt |
| snapshots | Data project | dbt |
| generic macros/load strategies | Framework | versioned dbt package |
| generic reusable workflows | Framework | reusable GitHub Actions |
| project tests/semantic definitions | Data project + framework primitives | dbt/SQL as appropriate |
| project ingestion config | Data project | technology-specific config/code |
| source simulator | Demo Source Systems | Python/runtime tooling |

No object is simultaneously authoritative in Terraform and dbt/SQL migrations.

## 8. Terraform boundary

Terraform owns stable platform infrastructure/access-control objects: databases, platform schemas, warehouses, roles, grants, workload identities/integrations, cost controls and reusable project bootstrap infrastructure.

dbt owns transformation-layer relations, snapshots and tests. Selected native operational procedures/tasks/alerts/recovery logic may be controlled Snowflake SQL where that is a clearer lifecycle owner.

## 9. Data project framework design

The framework is a **versioned dependency**, not a forever-copied folder. It will provide reusable dbt macros/tests, load/SCD2 strategies, reconciliation, freshness, audit/operations contracts, metadata schemas/validation, reusable GitHub Actions, rollback/recovery/backfill templates, bootstrap capability and reference examples.

Projects upgrade deliberately, e.g. `v1.2 -> v1.3`.

## 10. Metadata-driven design principles

Metadata defines stable technical behaviour: strategy, keys/composite keys, source relation, effective timestamp/watermark, tracked columns, delete/dedup policies, thresholds, reconciliation, quality, criticality and recovery targets.

Framework code may derive key hashes, MERGE/SCD2 mechanics, watermarks, audit columns, freshness, reconciliation, run logging and standard tests.

Business joins/calculations/domain rules remain explicit SQL/code.

Escape hatch:

```yaml
implementation: custom
```

Custom implementations still participate in standard contracts, testing, observability, reconciliation, audit and recovery.

## 11. RAW contracts

Project-owned RAW contracts define the boundary between ingestion and downstream engineering. Minimum contract fields: source system/owner, schema version, entity/table, grain, business key, required columns/types/nullability, source timestamp, CDC operation semantics, sequence/offset when relevant, cadence, retention, classification and breaking-change policy.

Typical technical fields:

```text
source_operation
source_sequence
source_updated_at
ingested_at
batch_id
source_system
```

Schema evolution distinguishes compatible vs breaking changes; contract validation becomes CI in Phase 2/3.

## 12. Ingestion patterns

All ingestion implementations converge on project RAW contracts:

```text
Synthetic generator ─┐
Snowpipe Streaming  ─┼─> RAW -> downstream dbt
Kafka Connector     ─┤
Openflow CDC        ─┘
```

Transport will compare direct Snowpipe Streaming and Kafka -> Snowflake Kafka Connector -> Snowpipe Streaming using the same logical event dataset. Only one path is normally active.

Health adds Openflow CDC only in the final ingestion phase after downstream Health already works.

## 13. dbt architecture

```text
RAW -> staging -> intermediate/canonical -> marts -> semantic
```

Use `source()`, `ref()`, generic/singular tests, source freshness, snapshots where appropriate, reusable macros, framework package dependencies and environment-aware schema generation. Never hard-code environment-specific database names in model SQL.

## 14. SCD2 strategy catalog

Dynamic Tables are explicitly excluded for SCD2.

Approved patterns:

1. `scd2_snapshot` — dbt Snapshot
2. `scd2_merge` — explicit dbt incremental/MERGE
3. `scd2_stream_task` — Snowflake Streams + Tasks

Common logical output where appropriate:

```text
business_key
effective_from
effective_to
is_current
record_hash
source_updated_at
loaded_at
source_system
```

Tests must cover initial/unchanged/changed records, composite keys, multiple changes, duplicates, late/out-of-order data, deletes, rerun/idempotency, backfill, partial failure and history rebuild.

## 15. CI/CD lifecycle

```text
feature branch
-> personal DEV
-> pull request
-> ephemeral PR CI
-> automated validation/testing
-> review + merge
-> shared DEV
-> UAT
-> approval
-> PROD
-> smoke/regression
```

PR close cleans ephemeral resources. CI/CD and operational scheduling remain separate concerns.

## 16. Release promotion

One Git history per project; no environment branches. Promote the exact same immutable `git_sha` through environments. Release/deployment history is persisted in `PLATFORM_CONTROL.DEPLOYMENT`.

## 17. Production rollback

For derived analytics data:

```text
pre-release zero-copy clone
-> deploy
-> smoke + DQ + reconciliation
-> PASS: keep release
-> FAIL: controlled SWAP to known-good state
-> validate + reconcile + resume
```

Do not blindly roll back RAW because new valid source data may have arrived. Distinguish code rollback, object recovery, data recovery and infrastructure recovery. After runtime rollback, Git desired state must be corrected through revert or fix-forward.

## 18. Data repair/recovery

Support bounded retry, checkpoint/watermark, replay, idempotent rerun, backfill, Time Travel, UNDROP, point-in-time/zero-copy clone recovery, affected-window rebuild and deterministic SCD2 history rebuild. Prefer these over ad-hoc production DML.

## 19. Data quality

Baseline: not-null, uniqueness, relationships, accepted values, domain assertions, volume checks, SCD2 invariants, schema contract checks and reconciliation. dbt tests alone are not considered full production reconciliation.

## 20. Reconciliation

Support row counts, distinct business-key counts, control totals, min/max business timestamp, watermarks, rejected rows and duplicates across boundaries such as RAW -> STAGING, STAGING -> CANONICAL and CANONICAL -> MART.

Results go to `PLATFORM_CONTROL.QUALITY.RECONCILIATION_RESULTS`.

## 21. Freshness

Track separately:

1. **source freshness** — age of newest source data;
2. **pipeline freshness** — last successfully processed source watermark;
3. **published dataset freshness** — currentness of consumer-ready data.

Pipeline success alone does not imply dataset readiness.

## 22. SLI / SLO / SLA

- **SLI** = measured signal.
- **SLO** = internal reliability objective.
- **SLA** = formal/business commitment; optional per dataset.

Metadata may define criticality, expected-ready-by, source/published max age, availability SLO, optional SLA and recovery target. Dataset readiness may require transformation, DQ, reconciliation, freshness and semantic regression checks all to pass.

## 23. Observability

Start with Snowflake-native telemetry/SQL, dbt artifacts, GitHub Actions and `PLATFORM_CONTROL`, not mandatory third-party tooling.

Monitor freshness, pipeline/task status, long-running work, dbt failures, DQ, reconciliation, publish readiness, warehouse/query usage, deployment/rollback/recovery, SLO breaches, cost anomalies and orphaned CI resources.

## 24. Incident management

```text
DETECT -> TRIAGE -> CONTAIN -> RECOVER -> RECONCILE -> VALIDATE -> RESUME -> CLOSE
```

Use practical incident tables, alerts and runbooks; do not build a custom ITSM platform.

## 25. Cost controls

Use workload-appropriate warehouses, `AUTO_SUSPEND`, `AUTO_RESUME`, sensible sizing, resource monitors/budgets where appropriate, warehouse/query reporting, project/cost-centre tags where useful, oversized-warehouse detection and orphaned-CI cleanup.

## 26. Semantic Views

Use Snowflake-native Semantic Views; Cube is excluded. Explore logical tables, dimensions, facts, metrics, relationships, semantic querying, verified queries, `AI_VERIFIED_QUERIES` and semantic regression testing. Prefer the project release lifecycle where practical.

## 27. Agency/project onboarding

A future `enterprise-snowflake-finance-analytics` should primarily add project config, dataset metadata, RAW contracts, source mappings, domain SQL, project tests, semantic definitions and source-specific ingestion config.

It should not reimplement generic CI/CD, SCD2, reconciliation, freshness, audit, recovery/rollback or Terraform project modules.

## 28. Implementation roadmap

- **Phase 0 — Architecture:** five-repo model, blueprint, naming, ownership/RBAC, metadata philosophy, ADRs, recovery/operations architecture. **Complete.**
- **Phase 1 — Platform Foundation:** NONPROD/PROD topology, Terraform baseline, databases/schemas/warehouses, `PLATFORM_CONTROL`, RBAC, workload identities, project bootstrap, cost guardrails.
- **Phase 2 — Framework Foundation:** metadata schemas/validation, dbt package, environment/schema macros, basic load strategies, reusable CI workflows, operational logging contract.
- **Phase 3 — Thin CI/CD Delivery Spine:** prove personal DEV -> PR CI -> shared DEV -> UAT -> PROD with exact Git SHA, release history, recovery point, smoke/rollback skeleton and cleanup.
- **Phase 4 — Health Vertical Slice:** deterministic Health RAW -> semantic with contracts, DQ, reconciliation, freshness/SLO, recovery/backfill and SCD2.
- **Phase 5 — Transport Streaming Vertical Slice:** direct Snowpipe Streaming, then Kafka Connector, same event contract/downstream pipeline.
- **Phase 6 — Complete Pattern Catalog:** `full_refresh`, `append_only`, `incremental_merge`, `scd2_snapshot`, `scd2_merge`, `scd2_stream_task`, schema evolution, late data, dedup, replay/backfill.
- **Phase 7 — Production Hardening:** masking/RAP/classification, cost monitoring, drift, central health views, incident alerts, recovery drills, SLO/SLA reporting.
- **Phase 8 — Openflow:** SQL Server -> Openflow CDC -> `HEALTH_RAW`, proving no downstream redesign.

## 29. ADR index

| ADR | Decision | Status |
|---|---|---|
| [ADR-001](adr/ADR-001-five-repository-architecture.md) | Five-repository architecture and ownership boundaries | Accepted |
| ADR-002 | Two-account NONPROD/PROD topology | Accepted; detailed file deferred until implementation details exist |
| ADR-003 | Capability account roles + database roles | Accepted; detailed file deferred |
| [ADR-004](adr/ADR-004-object-ownership-and-terraform-boundary.md) | Selective Terraform; one authoritative owner per object | Accepted |
| ADR-005 | Versioned framework rather than copy/paste | Accepted; detailed file deferred |
| [ADR-006](adr/ADR-006-metadata-driven-technical-behaviour.md) | Metadata for technical behaviour; code for business logic | Accepted |
| [ADR-007](adr/ADR-007-raw-contract-boundary.md) | RAW contract as ingestion/downstream boundary | Accepted |
| ADR-008 | Immutable Git SHA promotion; no environment branches | Accepted; detailed file deferred |
| ADR-009 | SCD2 catalog excludes Dynamic Tables | Accepted; detailed file deferred |
| ADR-010 | Derived-data rollback via clone + controlled SWAP | Accepted; detailed file deferred |
| ADR-011 | Git config truth; `PLATFORM_CONTROL` runtime truth | Accepted; detailed file deferred |
| ADR-012 | Snowflake-native observability baseline | Accepted; detailed file deferred |
| ADR-013 | Snowflake Semantic Views; Cube excluded | Accepted; detailed file deferred |
| ADR-014 | Same Transport RAW contract for direct/Kafka paths | Accepted; detailed file deferred |
| ADR-015 | Openflow deferred until final ingestion phase | Accepted; detailed file deferred |

Create separate ADR files when implementation introduces meaningful alternatives/consequences; do not create ceremonial ADR files with no new decision content.

## 30. Current status

### Phase 0 — COMPLETE (2026-08-28)

- [x] Five GitHub repositories created with canonical `enterprise-snowflake-*` naming.
- [x] Canonical `docs/PROJECT_BLUEPRINT.md` established.
- [x] Final five-repository responsibility model defined.
- [x] Initial repository skeletons defined.
- [x] Snowflake naming conventions documented in [`standards/NAMING_CONVENTIONS.md`](standards/NAMING_CONVENTIONS.md).
- [x] Initial object ownership/Terraform matrix defined.
- [x] Account Role / Database Role model defined.
- [x] Metadata-driven philosophy and `implementation: custom` escape hatch defined.
- [x] Initial ADR index defined.
- [x] High-value ADR files created for repo boundaries, ownership/Terraform, metadata and RAW contract.
- [x] CI/CD, rollback, recovery, reconciliation, freshness, observability and incident lifecycles defined at architecture level.
- [x] All five repository READMEs aligned to their responsibility boundaries.
- [x] Major infrastructure, Kafka, Snowpipe Streaming, Openflow and significant dbt implementation intentionally not started.

### Phase 0 exit criteria

All exit criteria are satisfied. Architecture and ownership are sufficiently explicit to begin Phase 1 without inventing project-specific infrastructure prematurely.

## 31. Next implementation step

Begin **Phase 1 — Platform Foundation** with the smallest useful slice in `enterprise-snowflake-platform-infra`:

1. pin Terraform and Snowflake provider versions;
2. establish `terraform/modules/` and `terraform/stacks/{nonprod,prod}/` only as needed by real code;
3. define environment configuration/variables without hard-coded credentials;
4. implement the minimum database/schema/warehouse foundation for NONPROD first;
5. define the initial RBAC hierarchy and grants in Terraform;
6. create the structural `PLATFORM_CONTROL` database/schemas, but defer rich operational table design until its first consumer exists;
7. add validation/format/plan CI without production deployment yet;
8. update this blueprint with the actual Phase 1 object ownership and implementation status.

Do **not** start Kafka, Snowpipe Streaming, Openflow or broad dbt modelling during this step.

---

## Appendix A — naming summary

Full standard: [`docs/standards/NAMING_CONVENTIONS.md`](standards/NAMING_CONVENTIONS.md).

Core patterns:

```text
Account roles:   AR_<SCOPE>_<CAPABILITY>
Database roles:  DR_<PROJECT>_ANALYTICS_<READ|WRITE|OWNER>
Warehouses:      WH_<SCOPE>_<WORKLOAD>
Personal schema: <DEVELOPER>_<LAYER>
PR CI schema:    PR_<NUMBER>_<LAYER>
```

Control schemas:

```text
PLATFORM_CONTROL.DEPLOYMENT
PLATFORM_CONTROL.QUALITY
PLATFORM_CONTROL.OBSERVABILITY
PLATFORM_CONTROL.OPERATIONS
```

## Appendix B — approved load strategies

```text
full_refresh
append_only
incremental_merge
scd2_snapshot
scd2_merge
scd2_stream_task
```

Each strategy receives a formal metadata contract during Phase 2.