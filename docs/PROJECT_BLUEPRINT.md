# Enterprise Snowflake Platform — Project Blueprint

> **Status:** Phase 0 — Architecture foundation
>
> **Authority:** This document is the canonical architecture memory for the Enterprise Snowflake Platform project. Major architectural decisions, implementation status, and the next implementation step must be reflected here after each meaningful change.
>
> **Repository:** `enterprise-snowflake-platform-infra`

## 1. Project goals

Build a production-grade, reusable Snowflake platform reference implementation that is credible for Senior/Principal Data Engineering and Snowflake Platform Engineering work, while remaining practical enough for a real organisation to adopt.

The platform should demonstrate:

- clear platform/project ownership boundaries;
- repeatable project onboarding;
- stable RAW contracts independent of ingestion technology;
- metadata-driven technical behaviour without turning metadata into a programming language;
- one Git history per project with immutable Git SHA promotion;
- production-quality CI/CD, recovery, reconciliation, freshness, observability, SLOs and cost controls;
- multiple valid implementation patterns where source characteristics genuinely differ;
- project autonomy inside central platform guardrails.

## 2. Non-goals

This project does not include Metric Guard and does not attempt to solve governed AI/API access, MCP/OpenAPI authorisation, or AI consumption governance.

Additional non-goals:

- maximising technology count for portfolio appearance;
- forcing every workload into one ingestion or SCD2 technology;
- Terraform-managing every Snowflake object;
- encoding complex business logic in YAML;
- using separate DEV/UAT/PROD code branches;
- using Dynamic Tables for SCD2;
- introducing Spark Streaming without a concrete requirement;
- making Marketplace Secure Shares part of the core ingestion architecture;
- building a full ITSM platform.

## 3. Architecture principles

1. **Convention over copy/paste.**
2. **Configuration for stable technical behaviour; code for genuine business differences.**
3. **Project autonomy inside platform guardrails.**
4. **Implementation diversity is acceptable; operational standards remain consistent.**
5. **RAW contracts isolate ingestion technology from downstream data engineering.**
6. **The same immutable Git SHA is promoted through DEV, UAT and PROD.**
7. **Human production authority and machine deployment identity are separate concepts.**
8. **Production readiness is defined by recoverability, not merely successful deployment.**
9. **One object has one authoritative owner.**
10. **Git is configuration source of truth; `PLATFORM_CONTROL` stores runtime/operational state.**
11. **Prefer deterministic repair over manual production DML.**
12. **Do not introduce technology without a concrete platform or workload requirement.**

## 4. Repository architecture

The canonical five repositories are:

| Repository | Primary owner | Purpose |
|---|---|---|
| `enterprise-snowflake-platform-infra` | Central Platform Engineering | Snowflake foundation, RBAC, shared governance, Terraform, control plane, observability, recovery architecture and canonical platform documentation |
| `enterprise-snowflake-data-project-framework` | Central Platform Engineering | Versioned golden-path capabilities consumed by project repos |
| `enterprise-snowflake-demo-source-systems` | Demo/test tooling | Deterministic source-system simulation only; responsibility stops at source/RAW boundary |
| `enterprise-snowflake-health-analytics` | Health data product/team | Traditional enterprise reference workload: batch/CDC, PII, SCD2, reconciliation and recovery |
| `enterprise-snowflake-transport-analytics` | Transport data product/team | Event/streaming reference workload: Snowpipe Streaming, Kafka Connector, out-of-order events and near-real-time SLOs |

### Final responsibility model

**Platform Infra owns** account/environment foundation, reusable infrastructure modules, account roles, shared governance, platform control schemas, central observability, cost guardrails, workload identities and platform-level recovery controls.

**Framework owns** generic dbt macros/tests, load strategy implementations, metadata schemas/validation, reusable CI/CD workflows, generic reconciliation/freshness/audit/operational contracts, rollback/recovery workflow templates and bootstrap tooling.

**Demo Source Systems owns** deterministic data generation, source mutations, database/file/event simulation, Kafka producers, direct Snowpipe Streaming producers and failure scenarios. It must never contain downstream dbt transformations, marts, semantic views or downstream reconciliation logic.

**Health owns** Health RAW contracts, Health source mappings/configuration, Health-specific SQL/business rules/tests, Health semantic definitions and Health-specific ingestion configuration.

**Transport owns** Transport RAW contracts, Transport source mappings/configuration, Transport-specific SQL/business rules/tests, Transport semantic definitions and Transport-specific ingestion configuration.

### Initial repository skeletons

```text
enterprise-snowflake-platform-infra/
├── README.md
├── docs/
│   ├── PROJECT_BLUEPRINT.md
│   ├── architecture/
│   ├── adr/
│   ├── standards/
│   └── runbooks/
├── terraform/
│   ├── modules/
│   └── stacks/{nonprod,prod}/
├── snowflake/{bootstrap,control,governance,monitoring,alerts,recovery}/
├── config/{projects,access-profiles,governance}/
├── observability/
└── .github/workflows/

enterprise-snowflake-data-project-framework/
├── README.md
├── dbt_package/{macros,tests}/
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
├── config/{project.yml,datasets,contracts/raw,operations}/
├── dbt/{models,snapshots,tests}/
├── ingestion/openflow/
└── .github/workflows/

enterprise-snowflake-transport-analytics/
├── README.md
├── config/{project.yml,datasets,contracts/raw,operations}/
├── dbt/{models,snapshots,tests}/
├── ingestion/{snowpipe_streaming,kafka}/
└── .github/workflows/
```

Directories are created only when they gain a real file; the architecture does not use empty placeholder directories as evidence of implementation.

## 5. Snowflake account/environment topology

Use a Snowflake Organization with two accounts:

```text
NONPROD account
├── ANALYTICS_DEV
├── ANALYTICS_CI
└── ANALYTICS_UAT

PROD account
└── ANALYTICS_PROD
```

`ANALYTICS_DEV` supports personal developer schemas plus shared DEV schemas. `ANALYTICS_CI` supports ephemeral PR schemas. `ANALYTICS_UAT` and `ANALYTICS_PROD` use stable release schemas.

Environment-specific database/schema naming is configuration-driven. dbt model SQL must not hard-code DEV/UAT/PROD database names.

## 6. RBAC/access model

Account roles describe capabilities, not employee seniority.

### Platform account roles

- `AR_PLATFORM_READER`
- `AR_PLATFORM_ENGINEER`
- `AR_PLATFORM_ADMIN`

### Project account roles

For project `<PROJECT>`:

- `AR_<PROJECT>_READER`
- `AR_<PROJECT>_DEVELOPER`
- `AR_<PROJECT>_ADMIN`

Examples:

- `AR_HEALTH_READER`, `AR_HEALTH_DEVELOPER`, `AR_HEALTH_ADMIN`
- `AR_TRANSPORT_READER`, `AR_TRANSPORT_DEVELOPER`, `AR_TRANSPORT_ADMIN`

`AR_PLATFORM_ADMIN` does not automatically imply `ACCOUNTADMIN`. `ACCOUNTADMIN` remains highly restricted.

A user may hold independent platform and project capabilities simultaneously.

### Database roles

Database roles represent object access rather than persona/workload capability:

- `DR_<PROJECT>_ANALYTICS_READ`
- `DR_<PROJECT>_ANALYTICS_WRITE`
- `DR_<PROJECT>_ANALYTICS_OWNER`

Account roles inherit the database roles appropriate to their capability.

## 7. Object ownership model

Initial authoritative ownership matrix:

| Object/capability | Authoritative owner | Delivery mechanism |
|---|---|---|
| Snowflake accounts / organisation-level foundation | Platform Infra | Terraform/manual bootstrap where provider boundary requires it |
| Analytics databases | Platform Infra | Terraform |
| Platform/control schemas | Platform Infra | Terraform / controlled Snowflake SQL |
| Project warehouses | Platform Infra | Terraform |
| Account roles | Platform Infra | Terraform |
| Database roles and grants | Platform Infra | Terraform |
| OIDC/workload identities/integrations | Platform Infra | Terraform |
| Resource monitors/budgets/central cost controls | Platform Infra | Terraform / Snowflake native |
| `PLATFORM_CONTROL` structural objects | Platform Infra | Terraform / controlled Snowflake SQL |
| Shared control procedures/tasks/alerts | Platform Infra | Snowflake SQL unless Terraform is clearly authoritative |
| dbt staging/intermediate/canonical/marts | Data project repo | dbt |
| dbt snapshots | Data project repo | dbt |
| Project data tests | Data project repo + Framework | dbt |
| Semantic Views | Data project repo, preferably via release lifecycle | dbt/SQL where practical |
| Generic macros/load strategies | Framework | versioned dbt package |
| Generic CI/CD workflows | Framework | reusable GitHub Actions |
| Project-specific ingestion config | Data project repo | technology-specific config/code |
| Source simulator | Demo Source Systems | Python/container/runtime tooling |

No object may be simultaneously managed as authoritative state by Terraform and dbt/SQL migrations.

## 8. Terraform boundary

Terraform owns stable platform infrastructure and access-control objects:

- databases;
- platform schemas;
- warehouses;
- account roles;
- database roles;
- grants;
- OIDC/workload identities;
- integrations;
- cost/resource controls;
- reusable project bootstrap infrastructure.

Terraform does not own routine dbt transformation models, snapshots, marts or project business logic. Native operational objects such as procedures/tasks/alerts may use controlled Snowflake SQL when that creates a clearer ownership/lifecycle boundary.

## 9. Data project framework design

The framework is a versioned dependency, not a folder copied into each project forever.

It will provide:

- dbt package and reusable macros;
- generic tests;
- load strategy implementations;
- SCD2 implementations;
- reconciliation/freshness/audit/operations capabilities;
- project/dataset metadata schemas and validation;
- reusable GitHub Actions workflows;
- rollback/recovery/backfill workflow templates;
- bootstrap/template capability;
- reference documentation and examples.

Projects upgrade framework versions deliberately, for example `v1.2 -> v1.3`.

## 10. Metadata-driven design principles

Metadata is for stable, repetitive technical behaviour. Explicit SQL/code is for genuine domain logic.

Metadata may define:

- dataset identity;
- source relation;
- load strategy;
- keys/composite keys;
- effective timestamp/watermark;
- tracked columns;
- delete strategy;
- deduplication policy;
- freshness thresholds;
- reconciliation checks;
- standard quality checks;
- criticality and recovery targets.

The framework may derive technical behaviour such as key hashing, MERGE mechanics, SCD2 mechanics, audit columns, freshness, reconciliation, run logging and standard tests from metadata.

It must not become a YAML programming language for arbitrary joins, business calculations or exceptional modelling logic.

Escape hatch:

```yaml
implementation: custom
```

A custom implementation still participates in standard contracts, testing, observability, reconciliation, audit and recovery.

## 11. RAW contracts

Downstream engineering depends on a stable RAW contract, not on ingestion technology.

A RAW contract belongs to the project repository and defines at minimum:

- source system and owner;
- schema version;
- table/entity;
- grain;
- business key;
- required columns and types;
- nullable rules;
- source timestamp;
- CDC operation semantics;
- source sequence/offset when applicable;
- expected cadence;
- retention expectation;
- data classification;
- breaking-change policy.

Typical technical fields:

- `source_operation`
- `source_sequence`
- `source_updated_at`
- `ingested_at`
- `batch_id`
- `source_system`

Schema evolution must explicitly distinguish compatible and breaking changes. Contract validation becomes part of CI in later phases.

## 12. Ingestion patterns

All supported ingestion mechanisms converge on stable project RAW contracts:

```text
Synthetic generator  ─┐
Snowpipe Streaming   ─┼─> RAW contract -> downstream platform
Kafka Connector      ─┤
Openflow CDC         ─┘
```

Transport will eventually implement both direct Snowpipe Streaming and Kafka -> Snowflake Kafka Connector -> Snowpipe Streaming using the same logical event contract and downstream pipeline. Only one path is normally active at once.

Health will later add Openflow CDC only after the downstream Health vertical slice already works independently.

## 13. dbt architecture

Standard flow:

```text
RAW -> staging -> intermediate/canonical -> marts -> semantic
```

Required practices:

- use `source()` and `ref()`;
- generic and singular tests where appropriate;
- source freshness;
- reusable framework macros;
- snapshots where the chosen pattern calls for them;
- environment-aware configuration/schema generation;
- framework package dependencies;
- no environment-specific database names hard-coded in model SQL.

## 14. SCD2 strategy catalog

Dynamic Tables are explicitly excluded for SCD2.

Approved production examples:

1. `scd2_snapshot` — dbt Snapshot;
2. `scd2_merge` — explicit dbt incremental/MERGE;
3. `scd2_stream_task` — Snowflake Streams + Tasks.

Where appropriate, all converge on the logical output contract:

- `business_key`
- `effective_from`
- `effective_to`
- `is_current`
- `record_hash`
- `source_updated_at`
- `loaded_at`
- `source_system`

Required test scenarios include initial insert, unchanged record, change, composite keys, multiple changes, duplicates, late/out-of-order events, deletes, rerun/idempotency, backfill, partial failure and history rebuild.

## 15. CI/CD lifecycle

```text
feature branch
  -> personal DEV
  -> pull request
  -> ephemeral PR CI
  -> automated validation/testing
  -> review/merge
  -> shared DEV
  -> UAT
  -> approval
  -> PROD
  -> smoke/regression
```

CI/CD is triggered by code lifecycle; operational scheduling is triggered by time/data events. They are separate concerns.

PR close must clean up ephemeral CI resources.

## 16. Release promotion

One Git history per project. No DEV/UAT/PROD code branches.

Promotion identifies and deploys the exact same immutable commit:

```text
git_sha = <immutable commit>
```

Release metadata is persisted in `PLATFORM_CONTROL.DEPLOYMENT`.

## 17. Production rollback

For derived analytics databases/schemas, the preferred release rollback pattern is:

```text
pre-release zero-copy clone
  -> deploy
  -> smoke + DQ + reconciliation
  -> PASS: retain release
  -> FAIL: controlled SWAP to known-good state
  -> validate + reconcile + resume
```

RAW is not blindly rolled back because it may have received valid source changes after deployment.

Distinguish code rollback, object recovery, data recovery and platform infrastructure recovery.

After runtime rollback, Git desired state must be corrected by revert or fix-forward.

## 18. Data repair/recovery

Supported patterns will include retry, checkpoint/watermark, replay, idempotent rerun, bounded backfill, deterministic history rebuild, Time Travel, UNDROP, point-in-time/zero-copy clone recovery and rebuild of derived layers from canonical/RAW.

Manual production `UPDATE`/`DELETE` is a last resort, not the default repair mechanism.

## 19. Data quality

Production baseline:

- not-null;
- uniqueness;
- relationships;
- accepted values;
- domain assertions;
- volume checks;
- SCD2 invariant checks;
- schema contract checks;
- reconciliation.

Passing dbt tests alone is not considered sufficient production reconciliation.

## 20. Reconciliation

The framework will support row count, distinct business-key count, control totals, min/max business timestamp, watermark, rejected-row count and duplicate count.

Typical boundaries:

- RAW -> STAGING;
- STAGING -> CANONICAL;
- CANONICAL -> MART.

Results are written to `PLATFORM_CONTROL.QUALITY.RECONCILIATION_RESULTS`.

## 21. Freshness

Track at least three distinct signals:

1. source freshness — age of newest available source data;
2. pipeline freshness — source watermark last successfully processed;
3. published dataset freshness — age/currentness of consumer-ready data.

A technically successful pipeline does not automatically mean a dataset is ready.

## 22. SLI / SLO / SLA

- **SLI:** measured reliability/freshness signal.
- **SLO:** internal reliability objective.
- **SLA:** explicit/formal business commitment; not every dataset has one.

Dataset metadata may define criticality, expected-ready-by time, freshness targets, SLO availability targets, optional SLA readiness commitments and recovery targets.

Dataset readiness may require transformation, DQ, reconciliation, freshness and critical semantic regression checks all to pass.

## 23. Observability

Baseline uses Snowflake-native telemetry/SQL, dbt artifacts, GitHub Actions and platform control tables before requiring third-party tools.

Monitor source/pipeline/published freshness, failed/long-running tasks, dbt failures, DQ, reconciliation, publish state, warehouse/query usage, deployment/rollback/recovery status, SLO breaches, cost anomalies and orphaned CI resources.

## 24. Incident management

Operational lifecycle:

```text
DETECT -> TRIAGE -> CONTAIN -> RECOVER -> RECONCILE -> VALIDATE -> RESUME -> CLOSE
```

The platform records incidents and links them to relevant pipeline, release, recovery and data-quality records. A practical incident table plus alerts/runbooks is sufficient.

## 25. Cost controls

Baseline controls:

- workload-appropriate warehouse separation;
- `AUTO_SUSPEND` / `AUTO_RESUME`;
- sensible default sizes;
- resource monitors/budgets where appropriate;
- warehouse/query usage reporting;
- project/cost-centre tagging where useful;
- detection of unexpected/oversized warehouses;
- cleanup of orphaned CI resources.

## 26. Semantic Views

Use Snowflake-native Semantic Views. Cube is out of scope.

Explore logical tables, dimensions, facts, metrics, relationships, semantic querying, verified queries, `AI_VERIFIED_QUERIES` and semantic regression testing.

Prefer management through the same project release lifecycle where practical.

## 27. Agency/project onboarding

A future project such as `enterprise-snowflake-finance-analytics` should primarily add:

- project configuration;
- dataset metadata;
- RAW contracts;
- source mappings;
- domain SQL;
- project-specific tests;
- semantic definitions;
- project-specific ingestion config where required.

It should consume versioned framework capabilities rather than reimplement CI/CD, SCD2 mechanics, reconciliation, freshness, audit logging, recovery/rollback workflows or Terraform project modules.

## 28. Implementation roadmap

### Phase 0 — Architecture

- establish five-repository boundaries;
- create this canonical blueprint;
- define naming conventions;
- define ownership matrix;
- define RBAC/database-role model;
- define metadata philosophy;
- establish initial ADRs;
- define operational/recovery architecture;
- stop before major infrastructure/pipelines.

### Phase 1 — Platform Foundation

NONPROD/PROD topology, Terraform baseline, databases/schemas/warehouses, `PLATFORM_CONTROL`, RBAC, OIDC/workload identities, project bootstrap and cost guardrails.

### Phase 2 — Framework Foundation

Metadata schemas/validation, dbt package, environment/schema macros, initial load strategies, reusable CI workflows and operational logging contract.

### Phase 3 — Thin CI/CD Delivery Spine

Prove personal DEV -> PR CI -> shared DEV -> UAT -> PROD with exact Git SHA, release history, pre-release recovery point, smoke test, rollback skeleton and CI cleanup.

### Phase 4 — Health Vertical Slice

Synthetic deterministic Health workload from RAW through semantic, including contracts, DQ, reconciliation, freshness/SLO, incident metadata, recovery/backfill and at least one SCD2 strategy.

### Phase 5 — Transport Streaming Vertical Slice

Direct Snowpipe Streaming first; then Kafka Connector using the same event contract/downstream pipeline. Demonstrate duplicates, out-of-order events, burst/reconnect/recovery and near-real-time freshness/SLOs.

### Phase 6 — Complete Pattern Catalog

Implement `full_refresh`, `append_only`, `incremental_merge`, `scd2_snapshot`, `scd2_merge`, `scd2_stream_task`, plus schema evolution, late data, deduplication, replay and backfill.

### Phase 7 — Production Hardening

Masking, row access, classification/tags, cost monitoring, drift checks, central health views, alerts, rollback/recovery exercises, failure injection and SLO/SLA reporting.

### Phase 8 — Openflow

Add SQL Server -> Openflow CDC -> `HEALTH_RAW` only after the downstream Health architecture is already proven.

## 29. ADR index

Initial ADRs:

| ADR | Decision | Status |
|---|---|---|
| ADR-001 | Five-repository architecture and ownership boundaries | Accepted |
| ADR-002 | Two-account NONPROD/PROD topology | Accepted |
| ADR-003 | Capability-based account roles plus database roles | Accepted |
| ADR-004 | Selective Terraform ownership; one authoritative owner per object | Accepted |
| ADR-005 | Versioned project framework rather than copy/paste | Accepted |
| ADR-006 | Metadata for stable technical behaviour; explicit code for business logic | Accepted |
| ADR-007 | RAW contract as ingestion/downstream boundary | Accepted |
| ADR-008 | Immutable Git SHA promotion; no environment branches | Accepted |
| ADR-009 | SCD2 catalog excludes Dynamic Tables | Accepted |
| ADR-010 | Derived-data rollback via pre-release clone + controlled SWAP | Accepted |
| ADR-011 | Git as configuration truth; `PLATFORM_CONTROL` as runtime/operational state | Accepted |
| ADR-012 | Snowflake-native observability baseline before third-party tooling | Accepted |
| ADR-013 | Snowflake-native Semantic Views; Cube excluded | Accepted |
| ADR-014 | Transport validates direct Snowpipe Streaming and Kafka Connector against the same RAW contract | Accepted |
| ADR-015 | Openflow deferred until the final ingestion phase | Accepted |

Individual ADR files will be created as decisions need detailed context, alternatives and consequences. This index is canonical until then.

## 30. Current status

### Phase 0 implementation status

- [x] Five canonical GitHub repositories created.
- [x] Canonical repository naming aligned to the `enterprise-snowflake-*` prefix.
- [x] Repository responsibility model defined.
- [x] Initial repository skeletons defined.
- [x] Snowflake account/environment topology defined.
- [x] Initial object ownership matrix defined.
- [x] Account Role / Database Role model defined.
- [x] Metadata schema philosophy defined.
- [x] Initial ADR list defined.
- [x] Recovery/rollback/observability architecture captured at blueprint level.
- [ ] Naming convention standard extracted into a dedicated standards document.
- [ ] Initial ADR files created for the highest-impact decisions.
- [ ] Phase 0 repository READMEs aligned to the canonical boundaries.

No Terraform infrastructure, Kafka, Snowpipe Streaming, Openflow or significant dbt model implementation has started.

### Phase 0 exit criteria

Phase 0 is complete when:

1. `PROJECT_BLUEPRINT.md` exists and is canonical;
2. all five repository responsibilities are explicit and non-overlapping;
3. initial repository skeletons are defined;
4. Snowflake naming conventions are documented;
5. authoritative object ownership is documented;
6. account-role/database-role model is documented;
7. metadata philosophy and escape hatch are documented;
8. initial ADRs exist for core cross-cutting decisions;
9. account/environment topology is documented;
10. CI/CD, rollback, recovery, observability and incident lifecycles are architecturally defined;
11. no major infrastructure or data pipeline implementation has begun.

## 31. Next implementation step

Finish Phase 0 documentation only:

1. add `docs/standards/NAMING_CONVENTIONS.md`;
2. create the first high-value ADR files for repository boundaries, ownership/Terraform boundary, metadata-driven design and RAW contracts;
3. add minimal README files to all five repos that point back to the canonical blueprint and restate each repo's boundary;
4. review Phase 0 exit criteria;
5. only then begin Phase 1 with the smallest Snowflake/Terraform foundation slice.

---

## Appendix A — Snowflake naming conventions (initial)

These conventions are canonical until the dedicated standards document supersedes this appendix.

### General rules

- Snowflake object names use uppercase `SNAKE_CASE`.
- Git repositories/files use lowercase kebab-case or ecosystem-standard names.
- Names describe capability/purpose, not employee seniority.
- Environment-specific physical names come from configuration.
- Avoid embedding implementation technology in downstream business object names unless technology is the object's purpose.

### Accounts / logical environments

- Accounts: `NONPROD`, `PROD` at the architectural level.
- Databases: `ANALYTICS_DEV`, `ANALYTICS_CI`, `ANALYTICS_UAT`, `ANALYTICS_PROD`.
- Central control database: `PLATFORM_CONTROL`.

### Project schemas

Stable environments use functional names such as:

- `STAGING`
- `INTERMEDIATE`
- `CANONICAL` where a separate canonical layer is warranted
- `MARTS`
- `SEMANTIC`

Personal DEV schemas are prefixed with developer identity, e.g. `ALICE_STAGING`.

PR CI schemas are prefixed with immutable PR context, e.g. `PR_123_STAGING`.

### Roles

- Account role: `AR_<SCOPE>_<CAPABILITY>`
- Database role: `DR_<PROJECT>_ANALYTICS_<ACCESS>`

Examples:

- `AR_PLATFORM_ENGINEER`
- `AR_HEALTH_DEVELOPER`
- `DR_HEALTH_ANALYTICS_READ`

### Warehouses

Use workload/purpose naming rather than team seniority, for example:

- `WH_PLATFORM_ADMIN`
- `WH_HEALTH_TRANSFORM`
- `WH_TRANSPORT_TRANSFORM`
- `WH_CI`

Exact warehouse topology and sizing are deferred to Phase 1.

### Control schemas

```text
PLATFORM_CONTROL.DEPLOYMENT
PLATFORM_CONTROL.QUALITY
PLATFORM_CONTROL.OBSERVABILITY
PLATFORM_CONTROL.OPERATIONS
```

Planned tables include:

```text
DEPLOYMENT.RELEASE_HISTORY
DEPLOYMENT.DEPLOYMENT_RUNS
DEPLOYMENT.ROLLBACK_HISTORY
QUALITY.TEST_RUNS
QUALITY.TEST_RESULTS
QUALITY.RECONCILIATION_RESULTS
QUALITY.DATA_INCIDENTS
OBSERVABILITY.DATASET_HEALTH
OBSERVABILITY.FRESHNESS_STATUS
OBSERVABILITY.PIPELINE_HEALTH
OBSERVABILITY.COST_STATUS
OPERATIONS.PIPELINE_RUNS
OPERATIONS.INCIDENTS
OPERATIONS.RECOVERY_RUNS
OPERATIONS.BACKFILL_RUNS
```

## Appendix B — approved load-strategy names

```text
full_refresh
append_only
incremental_merge
scd2_snapshot
scd2_merge
scd2_stream_task
```

Each strategy will receive a formal metadata contract in Phase 2.