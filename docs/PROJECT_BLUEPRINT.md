# Enterprise Snowflake Platform — Project Blueprint

> **Status:** Phase 1 in progress — three-account foundation, organization bootstrap, domain RBAC and workload warehouse model implemented in source; shared apply gated on state + workload identity
>
> **Authority:** Canonical architecture memory for the Enterprise Snowflake Platform. Update this file after each meaningful architecture or implementation step.
>
> **Canonical repository:** `enterprise-snowflake-platform-infra`

## 1. Project goals

Build a production-grade reusable Snowflake platform reference implementation suitable for real enterprise adoption and Senior/Principal Data Engineering / Snowflake Platform Engineering work.

Key outcomes: clear ownership, repeatable onboarding, stable RAW contracts, metadata-driven technical behaviour, immutable Git SHA promotion, recoverability, reconciliation, freshness/SLOs, observability, cost attribution and multiple production patterns where workloads genuinely differ.

## 2. Non-goals

- Do not merge Metric Guard into this project.
- Do not maximise technology count for appearance.
- Do not force all ingestion or SCD2 workloads into one implementation.
- Do not Terraform-manage every Snowflake object.
- Do not create a YAML programming language for business logic.
- Do not use DEV/UAT/PROD Git branches.
- Do not use Dynamic Tables for SCD2.
- Do not introduce Spark Streaming without a concrete requirement.
- Marketplace Secure Shares are not a core ingestion path.
- Do not build a custom ITSM platform.

## 3. Architecture principles

1. Convention over copy/paste.
2. Configuration for stable technical behaviour; code for genuine business differences.
3. Domain/project autonomy inside platform guardrails.
4. Implementation diversity is acceptable; operational standards remain consistent.
5. RAW contracts isolate ingestion technology from downstream engineering.
6. Promote the same immutable Git SHA through environments.
7. Human production authority and machine deployment identity are separate.
8. Production readiness is defined by recoverability, not deployment success alone.
9. One object has one authoritative owner.
10. Git is configuration source of truth; `PLATFORM_CONTROL` stores runtime/operational state.
11. Prefer deterministic repair over manual PROD DML.
12. Account, database, schema and warehouse boundaries solve different problems.
13. Cost attribution is multi-dimensional; do not create database-per-source only for chargeback.
14. Consumer access is narrower than engineering read access.

## 4. Repository architecture

| Repository | Responsibility |
|---|---|
| `enterprise-snowflake-platform-infra` | account/platform foundation, Terraform, central RBAC/governance/control plane/cost/recovery architecture |
| `enterprise-snowflake-data-project-framework` | versioned dbt/macros/tests/metadata/reusable delivery + recovery golden path |
| `enterprise-snowflake-demo-source-systems` | deterministic external source simulation only; stops at source/RAW boundary |
| `enterprise-snowflake-health-analytics` | Health contracts/config/business SQL/tests/semantic/ingestion config |
| `enterprise-snowflake-transport-analytics` | Transport contracts/config/business SQL/tests/semantic/streaming config |

Detailed target tree: [`architecture/REPOSITORY_LAYOUT.md`](architecture/REPOSITORY_LAYOUT.md).

## 5. Snowflake account topology

Canonical topology is three Snowflake accounts:

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

DEV hosts personal/shared development plus ephemeral PR CI. UAT is a separate production-like account so account-scoped identity, RBAC, integrations, parameters and operational configuration can be tested before PROD. CI is not a fourth account.

See ADR-018 and [`architecture/ACCOUNT_TOPOLOGY.md`](architecture/ACCOUNT_TOPOLOGY.md).

## 6. Database and schema boundary

Analytics database pattern:

```text
<ENVIRONMENT>_<DOMAIN>
```

A database represents environment × governed data product/domain, not a physical source system. Twenty MSSQL/MySQL/API sources do not imply twenty databases.

Stable transformation schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Published consumer schemas are initially:

```text
MARTS
SEMANTIC
```

Source-purpose RAW schemas are created only when a real source is onboarded, for example `RAW_EHR_MSSQL` or `RAW_INSURANCE_API`.

Personal DEV schema pattern inside `DEV_<DOMAIN>`:

```text
<DEVELOPER>_<LAYER>
```

PR CI schema pattern inside `CI_<DOMAIN>`:

```text
PR_<NUMBER>_<LAYER>
```

See ADR-019 and `NAMING_CONVENTIONS.md`.

## 7. RBAC/access model

Platform capability roles:

```text
AR_PLATFORM_READER
  -> AR_PLATFORM_ENGINEER
  -> AR_PLATFORM_ADMIN
```

Every domain receives its own hierarchy:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

Every domain database receives:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
  -> DR_<DOMAIN>_ANALYTICS_READ
  -> DR_<DOMAIN>_ANALYTICS_WRITE
  -> DR_<DOMAIN>_ANALYTICS_OWNER
```

`GUEST` is authenticated read-only business/consumer access to published schemas only. It is not Snowflake `PUBLIC` and is not anonymous access. Initial GUEST visibility is MARTS + SEMANTIC.

`READER` can inspect all stable domain schemas. DEV developers receive WRITE. UAT/PROD developers remain read-only by default; deployment will use machine identity. Domain authority never crosses into another domain unless explicitly granted.

Human user lifecycle should come from enterprise SSO/IdP/SCIM rather than employee records in Terraform.

See ADR-020 and [`architecture/RBAC_MODEL.md`](architecture/RBAC_MODEL.md).

## 8. Warehouse and cost boundary

Account identifies environment; warehouse identifies domain + workload:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
```

DEV additionally has:

```text
WH_<DOMAIN>_CI
```

Current examples:

```text
WH_HEALTH_QUERY
WH_HEALTH_TRANSFORM
WH_HEALTH_CI
WH_TRANSPORT_QUERY
WH_TRANSPORT_TRANSFORM
WH_TRANSPORT_CI
WH_PLATFORM_OPS
```

GUEST receives QUERY. READER inherits it. DEV DEVELOPER additionally receives TRANSFORM. UAT/PROD ADMIN temporarily receives TRANSFORM until machine deployment identity takes over. CI warehouses are machine-only.

Warehouse defaults remain conservative: XSMALL, auto-resume, 60-second auto-suspend, initially suspended, explicit statement timeout, no unnecessary multi-cluster/query acceleration.

## 9. Object ownership model

| Object/capability | Authoritative owner |
|---|---|
| Organization DEV/UAT/PROD account resources | Platform Infra organization Terraform root |
| Domain analytics databases | Terraform / Platform Infra |
| Stable structural schemas | Terraform / Platform Infra |
| Domain/platform warehouses | Terraform / Platform Infra |
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

## 10. Terraform boundary and roots

Current Terraform roots:

```text
terraform/stacks/organization/
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

`organization/` alone uses `ORGADMIN` and manages DEV/UAT/PROD account resources from `config/organization.yml`. The account resources use a bootstrap SERVICE administrator with RSA public-key material supplied outside Git and `prevent_destroy = true`. Normal account roots do not use ORGADMIN.

Current reusable modules:

```text
analytics-environment
warehouse
platform-control
rbac
```

Terraform CLI `1.16.0` and Snowflake provider `2.19.0` are pinned. Credentials/private keys/state are never committed.

See ADR-021.

## 11. Data project framework design

The framework is a versioned dependency, not a copied folder. It will provide reusable dbt macros/tests, load/SCD2 strategies, reconciliation/freshness/audit contracts, metadata validation, reusable GitHub workflows and rollback/recovery/backfill templates.

Projects upgrade deliberately by release/tag/SHA.

## 12. Metadata-driven design

Metadata configures stable technical behaviour: strategy, key/composite key, source relation, timestamp/watermark, tracked columns, delete/dedup policy, thresholds, reconciliation, quality, freshness, criticality and recovery targets.

Business joins/calculations/domain rules remain explicit SQL/code.

Escape hatch:

```yaml
implementation: custom
```

Custom implementations still participate in contracts, testing, observability, reconciliation, audit and recovery.

## 13. RAW contracts

Project-owned RAW contracts define the ingestion/downstream boundary: source, owner, schema version, entity/table, grain, business key, required columns/types/nullability, source timestamp, CDC semantics, sequence/offset, cadence, retention, classification and breaking-change policy.

Typical technical fields:

```text
source_operation
source_sequence
source_updated_at
ingested_at
batch_id
source_system
```

## 14. Ingestion patterns

All implementations converge on project RAW contracts:

```text
Synthetic/file/database source ─┐
Snowpipe Streaming             ─┼─> RAW -> downstream dbt
Kafka Connector                ─┤
Openflow CDC                   ─┘
```

Transport later compares direct Snowpipe Streaming with Kafka -> Snowflake Kafka Connector -> Snowpipe Streaming using the same logical event contract; normally one path is active.

Health adds Openflow only after the downstream Health pipeline is proven.

## 15. dbt architecture

```text
RAW -> staging -> intermediate/canonical -> marts -> semantic
```

Use `source()`, `ref()`, generic/singular tests, source freshness, snapshots where appropriate, framework dependencies and environment-aware database/schema resolution. Model SQL never hard-codes DEV/UAT/PROD physical names.

## 16. SCD2 strategy catalog

Dynamic Tables are excluded for SCD2.

Approved patterns:

```text
scd2_snapshot
scd2_merge
scd2_stream_task
```

Tests cover initial/unchanged/changed records, composite keys, multiple changes, duplicates, late/out-of-order data, deletes, idempotency, backfill, partial failure and deterministic history rebuild.

## 17. CI/CD lifecycle

```text
feature branch
-> personal/shared DEV (DEV account)
-> PR CI (CI_<DOMAIN> in DEV account)
-> review + merge
-> UAT account
-> approval
-> PROD account
-> smoke + regression + DQ + reconciliation
```

PR close removes ephemeral CI resources. CI/CD and operational scheduling remain separate concerns.

## 18. Release promotion

One Git history per project; no environment branches. Promote the exact same immutable `git_sha` through DEV -> CI -> UAT -> PROD. Deployment state is recorded in account-local `PLATFORM_CONTROL.DEPLOYMENT` once implemented.

## 19. Production rollback

For derived analytics data:

```text
pre-release zero-copy clone
-> deploy
-> smoke + DQ + reconciliation
-> PASS: retain release
-> FAIL: controlled SWAP to known-good state
-> validate + reconcile + resume
```

Do not blindly roll back RAW. Correct Git desired state after runtime rollback.

## 20. Data repair/recovery

Support bounded retry, checkpoint/watermark, replay, idempotent rerun, backfill, Time Travel, UNDROP, point-in-time/zero-copy clone recovery, affected-window rebuild and deterministic SCD2 history rebuild. Prefer these over manual PROD DML.

## 21. Data quality

Baseline: not-null, uniqueness, relationships, accepted values, domain assertions, volume checks, SCD2 invariants, schema contracts and reconciliation. dbt tests alone are not full production reconciliation.

## 22. Reconciliation

Support row counts, distinct business-key counts, control totals, min/max business timestamp, watermarks, rejected rows and duplicates across important boundaries. Results go to `PLATFORM_CONTROL.QUALITY.RECONCILIATION_RESULTS` once its first consumer is implemented.

## 23. Freshness

Track separately:

1. source freshness;
2. pipeline freshness / processed watermark;
3. published dataset freshness.

Pipeline success does not imply consumer readiness.

## 24. SLI / SLO / SLA

- SLI = measured signal.
- SLO = internal reliability objective.
- SLA = optional formal/business commitment.

Dataset readiness may require transformation, DQ, reconciliation, freshness and semantic regression all to pass.

## 25. Observability and incident lifecycle

Start Snowflake-native: account usage, query/warehouse history, dbt artifacts, GitHub Actions and `PLATFORM_CONTROL`.

Monitor freshness, pipelines/tasks, long-running work, dbt failures, DQ/reconciliation, publish readiness, warehouse/query usage, deployment/rollback/recovery, SLO breaches, cost anomalies and orphaned CI resources.

Incident lifecycle:

```text
DETECT -> TRIAGE -> CONTAIN -> RECOVER -> RECONCILE -> VALIDATE -> RESUME -> CLOSE
```

Do not build a custom ITSM system.

## 26. Cost attribution / recovery

Do not use database-per-source as the primary chargeback model.

Use complementary boundaries:

```text
Domain storage/recovery       -> domain database (DEV_HEALTH, PROD_TRANSPORT, ...)
Source/table storage detail   -> schema/table storage metrics
Compute                       -> domain/workload warehouse + query tags
Serverless ingestion/services -> Snowflake service usage history
```

Query tags should eventually carry domain/source/pipeline/dataset/run/release metadata so compute can be attributed below warehouse level.

Cost monitors, budgets and tags are Phase 1 hardening after required administrative/edition boundaries are verified.

## 27. Semantic Views

Use Snowflake-native Semantic Views; Cube is excluded. Semantic definitions participate in project release/regression lifecycle where practical.

## 28. Project/domain onboarding

A future Finance project should primarily add project metadata, RAW contracts/source mappings/domain SQL/tests/semantic definitions and source-specific ingestion config.

Platform onboarding derives:

```text
DEV_FINANCE
CI_FINANCE
UAT_FINANCE
PROD_FINANCE

AR_FINANCE_GUEST
AR_FINANCE_READER
AR_FINANCE_DEVELOPER
AR_FINANCE_ADMIN

WH_FINANCE_QUERY
WH_FINANCE_TRANSFORM
WH_FINANCE_CI   # DEV only
```

Adding another physical Finance source normally adds source metadata/RAW structures, not another environment database or bespoke RBAC framework.

Projects do not reimplement generic CI/CD, SCD2, reconciliation, freshness, audit, recovery or Terraform modules.

## 29. Implementation roadmap

- **Phase 0 — Architecture:** complete.
- **Phase 1 — Platform Foundation:** **in progress**; three-account/account-bootstrap/domain-RBAC/warehouse foundation implemented; state/WIF/apply/cost hardening pending.
- **Phase 2 — Framework Foundation:** metadata validation, dbt package, environment macros, basic loads, reusable CI, operational logging.
- **Phase 3 — Thin CI/CD spine:** prove DEV -> PR CI -> UAT -> PROD with exact SHA, history/recovery point/cleanup/rollback skeleton.
- **Phase 4 — Health vertical slice:** deterministic Health RAW -> semantic with contracts/DQ/reconciliation/freshness/recovery/SCD2.
- **Phase 5 — Transport streaming:** direct Snowpipe Streaming then Kafka Connector, same RAW event contract.
- **Phase 6 — Complete pattern catalog:** approved load/SCD2 patterns, late data/dedup/replay/backfill/schema evolution.
- **Phase 7 — Production hardening:** masking/RAP/classification/cost/drift/health views/alerts/recovery drills/SLO reporting.
- **Phase 8 — Openflow:** SQL Server -> Openflow CDC -> Health RAW without downstream redesign.

## 30. ADR index and current status

| ADR | Decision | Status |
|---|---|---|
| ADR-001 | five repository architecture | Accepted |
| ADR-002 | two-account topology | Superseded by ADR-018 |
| ADR-003 | capability account roles + database roles | Accepted; refined by ADR-020 |
| ADR-004 | selective Terraform / one owner | Accepted |
| ADR-006 | metadata technical behaviour, code business logic | Accepted |
| ADR-007 | RAW contract boundary | Accepted |
| ADR-016 | project-qualified schemas in shared databases | Superseded by ADR-019 |
| ADR-017 | shared apply requires remote state + workload identity | Accepted |
| ADR-018 | three-account DEV/UAT/PROD topology | Accepted |
| ADR-019 | environment × data-product database boundary | Accepted |
| ADR-020 | domain GUEST access + workload warehouses | Accepted |
| ADR-021 | isolated ORGADMIN organization bootstrap | Accepted |

### Phase 1 completed in source control

- [x] Terraform CLI `1.16.0` and Snowflake provider `2.19.0` pinned.
- [x] `config/organization.yml` plus `config/environments/{dev,uat,prod}.yml` implemented.
- [x] old NONPROD stack/config removed.
- [x] Organization Terraform root implemented with ORGADMIN isolation and `prevent_destroy`.
- [x] `analytics-environment`, `warehouse`, `platform-control`, `rbac` modules implemented.
- [x] DEV databases: `DEV_HEALTH`, `CI_HEALTH`, `DEV_TRANSPORT`, `CI_TRANSPORT`.
- [x] UAT databases: `UAT_HEALTH`, `UAT_TRANSPORT`.
- [x] PROD databases: `PROD_HEALTH`, `PROD_TRANSPORT`.
- [x] account-local `PLATFORM_CONTROL` structural schemas.
- [x] database -> owning-domain mapping prevents cross-domain database roles.
- [x] domain `GUEST -> READER -> DEVELOPER -> ADMIN` hierarchy implemented.
- [x] database `GUEST -> READ -> WRITE -> OWNER` hierarchy implemented.
- [x] GUEST restricted to configured published schemas (`MARTS`, `SEMANTIC`).
- [x] per-domain QUERY/TRANSFORM warehouses implemented; DEV adds per-domain CI warehouses.
- [x] DEV developers WRITE; UAT/PROD developers read-only by default.
- [x] credential-free Terraform CI matrix includes organization/DEV/UAT/PROD.
- [x] Kafka, Snowpipe Streaming, Openflow and broad dbt remain intentionally deferred.

Still required before Phase 1 exit:

- [ ] get Terraform `fmt/init/validate` actually executing; current GitHub-hosted runner issue still prevents steps from starting;
- [ ] generate and commit `.terraform.lock.hcl` for each root from a successful init;
- [ ] choose durable independent remote state for organization/DEV/UAT/PROD;
- [ ] implement GitHub -> Snowflake WIF/OIDC and least-privilege machine roles;
- [ ] securely execute organization bootstrap or import existing DEV/UAT/PROD accounts;
- [ ] produce/review/apply DEV plan first and verify Snowflake objects/grants;
- [ ] prove UAT before enabling protected PROD planning/apply;
- [ ] implement personal DEV and PR CI schema lifecycle outside long-lived Terraform state;
- [ ] add cost-control/resource-monitor/tagging baseline where administrative/edition boundaries permit.

## 31. Next implementation step

Continue Phase 1 in this order:

1. resolve/verify Terraform execution and generate lock files;
2. select/record remote-state backend with independent organization/DEV/UAT/PROD state;
3. implement WIF/OIDC and dedicated Terraform/deployment/CI machine roles;
4. execute or import organization accounts under controlled ORGADMIN bootstrap;
5. add plan-only CI for DEV, review/apply, then verify roles/databases/schemas/warehouses;
6. add query-tag and cost-control baseline;
7. prove UAT; only then enable protected PROD planning/apply;
8. update this blueprint after each proven step.

Do **not** start Kafka, Snowpipe Streaming, Openflow or broad dbt modelling during this step.
