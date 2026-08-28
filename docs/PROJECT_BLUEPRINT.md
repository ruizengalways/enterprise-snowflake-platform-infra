# Enterprise Snowflake Platform — Project Blueprint

> **Status:** Phase 1 in progress — Terraform foundation code implemented; shared apply gated on remote state + workload identity
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

Detailed target layout: [`architecture/REPOSITORY_LAYOUT.md`](architecture/REPOSITORY_LAYOUT.md).

Key structure rules:

- Git directories appear only when they gain real content; no `.gitkeep` theatre.
- reusable GitHub workflows live under `.github/workflows/`;
- Terraform root stacks live under `terraform/stacks/{nonprod,prod}`;
- project repositories remain thin;
- `snowflake/monitoring/` owns native monitoring SQL until a genuinely separate observability asset type exists.

## 5. Snowflake account/environment topology

Use two Snowflake accounts:

```text
NONPROD
├── ANALYTICS_DEV
├── ANALYTICS_CI
├── ANALYTICS_UAT
└── PLATFORM_CONTROL

PROD
├── ANALYTICS_PROD
└── PLATFORM_CONTROL
```

Detailed executable baseline: [`architecture/ACCOUNT_TOPOLOGY.md`](architecture/ACCOUNT_TOPOLOGY.md).

Analytics databases are shared by project repositories, so stable schemas are project-qualified:

```text
HEALTH_STAGING
HEALTH_INTERMEDIATE
HEALTH_CANONICAL
HEALTH_MARTS
HEALTH_SEMANTIC

TRANSPORT_STAGING
TRANSPORT_INTERMEDIATE
TRANSPORT_CANONICAL
TRANSPORT_MARTS
TRANSPORT_SEMANTIC
```

Personal DEV schema pattern:

```text
<DEVELOPER>_<PROJECT>_<LAYER>
```

PR CI schema pattern:

```text
<PROJECT>_PR_<NUMBER>_<LAYER>
```

`ANALYTICS_CI` is Terraform-managed, but ephemeral PR schemas are not long-lived Terraform resources. Physical environment names are configuration-driven; dbt SQL never hard-codes environment database names.

## 6. RBAC/access model

Detailed executable baseline: [`architecture/RBAC_MODEL.md`](architecture/RBAC_MODEL.md).

Capability account roles:

```text
AR_PLATFORM_READER
AR_PLATFORM_ENGINEER
AR_PLATFORM_ADMIN

AR_<PROJECT>_READER
AR_<PROJECT>_DEVELOPER
AR_<PROJECT>_ADMIN
```

Database roles in each analytics database:

```text
DR_<PROJECT>_ANALYTICS_READ
DR_<PROJECT>_ANALYTICS_WRITE
DR_<PROJECT>_ANALYTICS_OWNER
```

Inheritance:

```text
READ -> WRITE -> OWNER
READER -> DEVELOPER -> ADMIN
```

NONPROD developers receive WRITE. PROD developers remain read-only; Project Admin receives OWNER. Platform roles and project roles are independent. `AR_PLATFORM_ADMIN` is not synonymous with `ACCOUNTADMIN` and does not automatically inherit all project admin roles.

CI warehouses are reserved for future machine identities, not normal human roles.

## 7. Object ownership model

| Object/capability | Authoritative owner | Mechanism |
|---|---|---|
| Organisation/account foundation | Platform Infra | Terraform/manual bootstrap where required |
| Analytics databases | Platform Infra | Terraform |
| Stable analytics schemas | Platform Infra lifecycle ownership | Terraform |
| Platform/control schemas | Platform Infra | Terraform / controlled SQL |
| Warehouses | Platform Infra | Terraform |
| Account roles | Platform Infra | Terraform |
| Database roles/grants | Platform Infra | Terraform |
| OIDC/workload identities/integrations | Platform Infra | Terraform |
| Resource monitors/budgets/cost controls | Platform Infra | Terraform / Snowflake native |
| `PLATFORM_CONTROL` structure | Platform Infra | Terraform / controlled SQL |
| Shared procedures/tasks/alerts | Platform Infra | controlled Snowflake SQL unless Terraform is explicitly selected |
| staging/intermediate/canonical/marts relations | Data project | dbt |
| snapshots | Data project | dbt |
| generic macros/load strategies | Framework | versioned dbt package |
| generic reusable workflows | Framework | reusable GitHub Actions |
| project tests/semantic definitions | Data project + framework primitives | dbt/SQL as appropriate |
| project ingestion config | Data project | technology-specific config/code |
| source simulator | Demo Source Systems | Python/runtime tooling |

Stable schema ownership is not transferred silently to project database roles; project roles receive governed privileges. One object is never simultaneously authoritative in Terraform and dbt/SQL migrations.

## 8. Terraform boundary

Terraform owns stable platform infrastructure/access-control objects: databases, stable schemas, warehouses, roles, grants, workload identities/integrations, cost controls and reusable project bootstrap infrastructure.

Current baseline:

```text
Terraform CLI:              1.16.0
Snowflake provider:         snowflakedb/snowflake 2.19.0
```

Root stacks pin exact versions. Environment object names/guardrails are loaded from `config/environments/{nonprod,prod}.yml` using `yamldecode()`.

Provider aliases separate administrative concerns:

```text
snowflake.sysadmin
snowflake.securityadmin
```

No credentials are committed.

Per ADR-017, automated apply is disabled until durable remote state and workload identity federation are established. CI currently runs credential-free format/init/validate only.

Detailed standard: [`standards/TERRAFORM_STANDARDS.md`](standards/TERRAFORM_STANDARDS.md).

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

Phase 2 schema-generation macros must implement ADR-016 project qualification.

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

Platform Terraform currently has validation CI only; deployment/promotion CI is Phase 3 after state/auth foundations are proven.

## 16. Release promotion

One Git history per project; no environment branches. Promote the exact same immutable `git_sha` through environments. Release/deployment history is persisted in `PLATFORM_CONTROL.DEPLOYMENT` once the first deployment consumer is implemented.

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

Results go to `PLATFORM_CONTROL.QUALITY.RECONCILIATION_RESULTS` once the quality runtime schema receives its first real consumer.

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

Initial warehouse guardrails are implemented in Terraform:

- standard warehouse type;
- conservative `XSMALL` size;
- `AUTO_RESUME` enabled;
- normally 60-second auto-suspend;
- initially suspended;
- explicit statement timeout;
- no query acceleration or multi-cluster scaling by default.

NONPROD project warehouses are separated for DEV/CI/UAT. PROD project warehouses separate transform/query workloads. Resource monitors/budgets/tags remain a later Phase 1 step because provider management can require stronger administration and should not force normal Terraform execution into `ACCOUNTADMIN`.

## 26. Semantic Views

Use Snowflake-native Semantic Views; Cube is excluded. Explore logical tables, dimensions, facts, metrics, relationships, semantic querying, verified queries, `AI_VERIFIED_QUERIES` and semantic regression testing. Prefer the project release lifecycle where practical.

## 27. Agency/project onboarding

A future `enterprise-snowflake-finance-analytics` should primarily add project config, dataset metadata, RAW contracts, source mappings, domain SQL, project tests, semantic definitions and source-specific ingestion config.

It should not reimplement generic CI/CD, SCD2, reconciliation, freshness, audit, recovery/rollback or Terraform project modules.

Project code is now also a required namespace discriminator for shared-environment schema naming.

## 28. Implementation roadmap

- **Phase 0 — Architecture:** five-repo model, blueprint, naming, ownership/RBAC, metadata philosophy, ADRs, recovery/operations architecture. **Complete.**
- **Phase 1 — Platform Foundation:** NONPROD/PROD topology, Terraform baseline, databases/schemas/warehouses, `PLATFORM_CONTROL`, RBAC, workload identities, project bootstrap, cost guardrails. **In progress; Terraform foundation code complete, apply/auth/state/cost hardening pending.**
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
| [ADR-002](adr/ADR-002-two-account-nonprod-prod-topology.md) | Two-account NONPROD/PROD topology | Accepted |
| [ADR-003](adr/ADR-003-capability-account-roles-and-database-roles.md) | Capability account roles + database roles; PROD developer read-only | Accepted |
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
| [ADR-016](adr/ADR-016-project-qualified-schemas-in-shared-environment-databases.md) | Project-qualified schemas in shared analytics databases | Accepted |
| [ADR-017](adr/ADR-017-terraform-apply-requires-remote-state-and-workload-identity.md) | Terraform apply requires remote state + workload identity | Accepted |

Create separate ADR files when implementation introduces meaningful alternatives/consequences; do not create ceremonial ADR files with no new decision content.

## 30. Current status

### Phase 0 — COMPLETE (2026-08-28)

- [x] Five GitHub repositories created with canonical `enterprise-snowflake-*` naming.
- [x] Canonical `docs/PROJECT_BLUEPRINT.md` established.
- [x] Final five-repository responsibility model defined.
- [x] Detailed repository layout planned.
- [x] Snowflake naming conventions documented.
- [x] Initial object ownership/Terraform matrix defined.
- [x] Account Role / Database Role model defined.
- [x] Metadata-driven philosophy and `implementation: custom` escape hatch defined.
- [x] Initial ADR set defined.
- [x] CI/CD, rollback, recovery, reconciliation, freshness, observability and incident lifecycles defined at architecture level.
- [x] All five repository READMEs aligned to their responsibility boundaries.

### Phase 1 — IN PROGRESS (2026-08-28)

Completed in source control:

- [x] Terraform CLI pinned to `1.16.0` via `.terraform-version` and root constraints.
- [x] Snowflake provider pinned exactly to `snowflakedb/snowflake` `2.19.0` in root stacks.
- [x] `.gitignore` protects state, plans, local tfvars and private keys; lock files remain committable.
- [x] `config/environments/nonprod.yml` and `prod.yml` established as non-secret infrastructure metadata.
- [x] project-qualified schema naming adopted to prevent Health/Transport and PR collisions.
- [x] reusable `analytics-environment` module implemented.
- [x] reusable `warehouse` guardrail module implemented.
- [x] reusable `platform-control` structural module implemented.
- [x] reusable `rbac` module implemented with account-role hierarchy, database-role hierarchy, baseline READ/WRITE grants and warehouse usage grants.
- [x] NONPROD root stack composes `ANALYTICS_DEV`, `ANALYTICS_CI`, `ANALYTICS_UAT`, warehouses, `PLATFORM_CONTROL`, and RBAC.
- [x] PROD root stack composes `ANALYTICS_PROD`, warehouses, `PLATFORM_CONTROL`, and stricter RBAC.
- [x] credential-free GitHub Actions Terraform `fmt`/`init -backend=false`/`validate` workflow added.
- [x] account topology, RBAC model and Terraform standards documented.
- [x] `ACCOUNTADMIN` intentionally excluded from normal Terraform providers.
- [x] Kafka, Snowpipe Streaming, Openflow and broad dbt implementation still intentionally untouched.

Still required before Phase 1 exit:

- [ ] generate/commit `.terraform.lock.hcl` from a successful connected `terraform init` and confirm CI validation succeeds;
- [ ] select and implement durable remote Terraform state with locking/recovery;
- [ ] implement GitHub -> Snowflake workload identity federation and dedicated machine roles;
- [ ] produce/review/apply the first NONPROD Terraform plan;
- [ ] verify resulting role/grant topology in Snowflake;
- [ ] implement project/bootstrap lifecycle needed for personal DEV/CI schema creation without putting ephemeral schemas in Terraform state;
- [ ] add cost monitor/budget/tag controls where the account edition/admin boundary supports them;
- [ ] enable PROD planning only after NONPROD state/auth/apply is proven.

## 31. Next implementation step

Continue **Phase 1** with the state/auth/apply spine rather than starting data pipelines:

1. validate the newly added Terraform workflow and fix any provider/HCL issues;
2. generate and commit provider lock files;
3. choose a durable remote-state backend based on the actual hosting/security boundary, then record the backend ADR;
4. implement `terraform/modules/workload-identity/` for GitHub-to-Snowflake WIF and narrow Terraform execution roles;
5. add plan-only CI for NONPROD using short-lived identity and remote state;
6. review the NONPROD plan before any apply;
7. only after successful NONPROD apply, add cost-control resources and PROD plan gating;
8. update this blueprint after each proven step.

Do **not** start Kafka, Snowpipe Streaming, Openflow or broad dbt modelling during this step.

---

## Appendix A — naming summary

Full standard: [`docs/standards/NAMING_CONVENTIONS.md`](standards/NAMING_CONVENTIONS.md).

Core patterns:

```text
Account roles:   AR_<SCOPE>_<CAPABILITY>
Database roles:  DR_<PROJECT>_ANALYTICS_<READ|WRITE|OWNER>
Warehouses:      WH_<SCOPE>_<WORKLOAD>
Stable schema:   <PROJECT>_<LAYER>
Personal schema: <DEVELOPER>_<PROJECT>_<LAYER>
PR CI schema:    <PROJECT>_PR_<NUMBER>_<LAYER>
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
