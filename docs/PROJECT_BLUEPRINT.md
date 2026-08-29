# Enterprise Snowflake Platform — Project Blueprint

> **Status:** Phase 1 in progress — static Terraform/state/WIF spine implemented; real remote-state control plane and DEV plan/apply remain
>
> **Authority:** Canonical long-term architecture for the Enterprise Snowflake Platform.
>
> **Fast handoff:** Read [`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) first in a new conversation/session.

## 1. Project goals

Build a production-grade reusable Snowflake platform reference implementation suitable for real enterprise adoption and Senior/Principal Data Engineering / Snowflake Platform Engineering work.

Key outcomes:

- clear platform/domain ownership;
- repeatable domain/source onboarding;
- stable RAW contracts independent of ingestion technology;
- metadata-driven technical behaviour without hiding business logic;
- immutable Git SHA promotion;
- strong DEV/UAT/PROD isolation;
- recoverability, reconciliation and freshness/SLOs;
- operational observability and cost attribution;
- multiple production patterns where workloads genuinely differ.

## 2. Non-goals

- Do not merge Metric Guard into this project.
- Do not maximise technology count for appearance.
- Do not force all ingestion/SCD2 workloads into one implementation.
- Do not Terraform-manage every Snowflake object.
- Do not create a YAML programming language for business logic.
- Do not use DEV/UAT/PROD Git branches.
- Do not use Dynamic Tables for SCD2.
- Do not introduce Spark Streaming without a concrete requirement.
- Marketplace Secure Shares are not a core ingestion path.
- Do not build a custom ITSM platform.
- Do not require AWS merely to run the Snowflake platform.
- Do not use OneDrive/SharePoint as live Terraform state storage.

## 3. Core architecture principles

1. Convention over copy/paste.
2. Configuration for stable technical behaviour; code for genuine business differences.
3. Domain/project autonomy inside platform guardrails.
4. RAW contracts isolate ingestion technology from downstream engineering.
5. Promote the same immutable Git SHA through environments.
6. Human identity and machine deployment identity are separate.
7. Production readiness is defined by recoverability, not deployment success alone.
8. One object has one authoritative lifecycle owner.
9. Git is configuration source of truth; `PLATFORM_CONTROL` stores runtime/operational state.
10. Prefer deterministic repair over manual PROD DML.
11. Account, database, schema, role and warehouse boundaries solve different problems.
12. Cost attribution is multi-dimensional; do not create database-per-source only for chargeback.
13. Consumer access is narrower than engineering read access.
14. Bootstrap state/identity are isolated from routine automation that consumes them.
15. Long-lived CI credentials are avoided where workload federation is available.
16. Terraform state backend selection is an execution concern, not Snowflake domain logic.

## 4. Repository architecture

| Repository | Responsibility |
|---|---|
| `enterprise-snowflake-platform-infra` | Snowflake account/platform foundation, Terraform, central RBAC/governance/control-plane/cost/recovery architecture |
| `enterprise-snowflake-data-project-framework` | versioned reusable dbt/macros/tests/metadata/delivery/recovery patterns |
| `enterprise-snowflake-demo-source-systems` | deterministic external-style source simulation only; stops at source/RAW boundary |
| `enterprise-snowflake-health-analytics` | Health contracts/config/business SQL/tests/semantic/ingestion config |
| `enterprise-snowflake-transport-analytics` | Transport contracts/config/business SQL/tests/semantic/streaming config |

Detailed layout: [`architecture/REPOSITORY_LAYOUT.md`](architecture/REPOSITORY_LAYOUT.md).

## 5. Snowflake account topology

Canonical topology:

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

Database pattern:

```text
<ENVIRONMENT>_<DOMAIN>
```

A database represents environment × governed data product/domain, not a physical source system.

Stable transformation schemas:

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

RAW schemas are introduced when a real source is onboarded, for example:

```text
RAW_EHR_MSSQL
RAW_INSURANCE_API
RAW_VEHICLE_API
```

Personal DEV schema pattern:

```text
<DEVELOPER>_<LAYER>
```

PR CI schema pattern:

```text
PR_<NUMBER>_<LAYER>
```

CI databases publish no human-consumer schemas; domain GUEST roles receive no CI database access.

See ADR-019.

## 7. Domain RBAC

Platform capability roles:

```text
AR_PLATFORM_READER
  -> AR_PLATFORM_ENGINEER
  -> AR_PLATFORM_ADMIN
```

Every domain receives:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

Each domain database receives only its owning domain's hierarchy:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
  -> DR_<DOMAIN>_ANALYTICS_READ
  -> DR_<DOMAIN>_ANALYTICS_WRITE
  -> DR_<DOMAIN>_ANALYTICS_OWNER
```

`GUEST` is authenticated business/consumer read-only access to published schemas only. It is not Snowflake `PUBLIC` and is not anonymous.

`READER` can inspect all stable domain schemas. DEV developers receive WRITE. UAT/PROD developers remain read-only by default.

Domain authority never crosses into another domain unless explicitly granted.

See ADR-020 and [`architecture/RBAC_MODEL.md`](architecture/RBAC_MODEL.md).

## 8. Human identity and employee membership

Terraform defines the RBAC model, privileges and warehouse grants. It does not manage everyday employee membership.

Target enterprise flow:

```text
Employee / contractor
    -> Entra ID / Okta group
        -> SCIM / approved identity provisioning
            -> AR_<DOMAIN>_<CAPABILITY>
```

Example:

```text
SNOWFLAKE_FINANCE_DEVELOPER -> AR_FINANCE_DEVELOPER
```

Adding/removing a person from an existing domain should be an identity-governance operation, not a Terraform code change.

A **new domain** is different: platform Terraform provisions its standard databases, roles, database roles and warehouses once.

## 9. Warehouse and cost boundary

Account identifies environment; warehouse identifies domain + workload:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
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

GUEST receives QUERY. READER inherits it. DEV DEVELOPER additionally receives TRANSFORM. UAT/PROD ADMIN currently receives TRANSFORM as a transitional human path until project deployment identities are implemented. CI warehouses are machine-only.

Warehouse defaults: XSMALL, auto-resume, 60-second auto-suspend, initially suspended, explicit statement timeout, no unnecessary multi-cluster/query acceleration.

## 10. Object ownership model

| Object/capability | Authoritative owner |
|---|---|
| DEV/UAT/PROD Snowflake account resources | organization Terraform root |
| platform Terraform SERVICE users / WIF trust / `AR_TERRAFORM_<ENV>` | identity bootstrap roots |
| domain analytics databases | routine Platform Infra Terraform |
| stable structural schemas | routine Platform Infra Terraform |
| domain/platform warehouses | routine Platform Infra Terraform |
| account roles/database roles/grants | routine Platform Infra Terraform |
| employee membership | enterprise IdP/SCIM/IAM process |
| `PLATFORM_CONTROL` structure | routine Platform Infra Terraform |
| selected shared procedures/tasks/alerts | controlled native Snowflake SQL when clearer than Terraform |
| staging/intermediate/canonical/marts relations | data project via dbt |
| reusable technical macros/tests | Framework |
| project tests/semantic definitions | project + framework primitives |
| source simulator | Demo Source Systems |

No object is simultaneously authoritative in Terraform and dbt/ad-hoc SQL.

## 11. Terraform roots and machine identity

Current lifecycle roots:

```text
terraform/stacks/organization/
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

### Organization bootstrap

`organization/` alone uses ORGADMIN and manages DEV/UAT/PROD account resources from `config/organization.yml`. Account resources use `prevent_destroy`.

### Identity bootstrap

`identity/<env>/` may activate ACCOUNTADMIN only to establish the routine Terraform machine identity:

```text
DEV   SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
UAT   SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
PROD  SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Service users and machine roles use `prevent_destroy`.

### Routine roots

`dev/uat/prod` activate only `AR_TERRAFORM_<ENV>` through `snowflake.objects` and `snowflake.security` provider aliases.

Initial routine account privileges:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Do not widen them without a demonstrated requirement from a real plan/apply.

See ADR-021 and ADR-023.

## 12. Terraform remote state

The Snowflake platform is **backend-agnostic**.

Supported reference profiles:

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS reference)
```

Terraform backend type cannot be selected by an input variable, so roots contain no committed cloud-specific backend block. Execution uses:

```text
terraform/backend-profiles/azurerm/backend.tf
terraform/backend-profiles/s3/backend.tf
terraform/scripts/select-backend.sh
```

to materialise an ignored `backend.generated.tf` before remote init.

### Azure Blob reference

```text
GitHub OIDC
    -> Microsoft Entra workload federation
        -> Azure Blob state
```

Use Entra/OIDC rather than a long-lived client secret. Baseline data-plane access is `Storage Blob Data Contributor` scoped to the state container. Azure Blob supplies native Terraform state locking/consistency behavior.

### S3 reference

```text
GitHub OIDC
    -> AWS IAM
        -> S3 state + .tflock
```

S3 requires versioning, encryption, public-access blocking and restricted object-prefix access. Terraform uses native `use_lockfile = true`; new deployments do not add deprecated DynamoDB locking.

### OneDrive / SharePoint

OneDrive/SharePoint may store architecture documents, runbooks, approvals and audit evidence. They are not the authoritative live Terraform state backend.

### State boundaries

Whichever backend is chosen:

```text
enterprise-snowflake-platform-infra/organization/terraform.tfstate
enterprise-snowflake-platform-infra/identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/identity/uat/terraform.tfstate
enterprise-snowflake-platform-infra/identity/prod/terraform.tfstate
enterprise-snowflake-platform-infra/platform/dev/terraform.tfstate
enterprise-snowflake-platform-infra/platform/uat/terraform.tfstate
enterprise-snowflake-platform-infra/platform/prod/terraform.tfstate
```

One deployment has one writable source of truth. Changing backend is a controlled Terraform state migration, not a normal toggle.

See ADR-024 and [`architecture/TERRAFORM_STATE_AND_IDENTITY.md`](architecture/TERRAFORM_STATE_AND_IDENTITY.md).

## 13. Metadata-driven design

Metadata configures stable technical behaviour:

```text
load/SCD2 strategy
business/composite key
source relation
timestamp/watermark
tracked columns
delete/dedup policy
freshness thresholds
reconciliation controls
criticality/recovery targets
```

Business joins/calculations/domain rules remain explicit SQL/code.

Escape hatch:

```yaml
implementation: custom
```

Custom implementations still participate in contracts, testing, observability, reconciliation, audit and recovery.

## 14. RAW contracts

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

## 15. Ingestion patterns

All ingestion implementations converge on project RAW contracts:

```text
Synthetic/file/database source ─┐
Snowpipe Streaming             ─┼─> RAW -> downstream dbt
Kafka Connector                ─┤
Openflow CDC                   ─┘
```

Transport later compares direct Snowpipe Streaming with Kafka -> Snowflake Kafka Connector -> Snowpipe Streaming using the same logical event contract.

Health adds Openflow only after the downstream Health pipeline is proven.

## 16. dbt and SCD2 architecture

```text
RAW -> staging -> intermediate/canonical -> marts -> semantic
```

Use `source()`, `ref()`, tests, source freshness, snapshots where appropriate, framework dependencies and environment-aware resolution. Model SQL never hard-codes physical DEV/UAT/PROD target names.

Approved SCD2 patterns:

```text
scd2_snapshot
scd2_merge
scd2_stream_task
```

Dynamic Tables are excluded for SCD2.

## 17. CI/CD and promotion

Data-project delivery:

```text
feature branch
-> personal/shared DEV
-> PR CI in CI_<DOMAIN>
-> merge
-> UAT
-> approval
-> PROD
-> smoke + regression + DQ + reconciliation
```

Exact immutable Git SHA is promoted through environments; no environment branches.

Platform Terraform progression:

```text
static CI
-> selected remote-state control plane
-> organization bootstrap/import
-> DEV identity bootstrap
-> manual DEV remote plan
-> reviewed DEV apply
-> Snowflake verification
-> UAT
-> PROD
```

`.github/workflows/terraform-plan-dev.yml` is manual-only, supports Azure Blob or S3 state, uses Snowflake WIF independently, and performs no apply.

## 18. Recovery and rollback

For derived analytics data:

```text
pre-release zero-copy clone
-> deploy
-> smoke + DQ + reconciliation
-> PASS: retain release
-> FAIL: controlled SWAP to known-good state
-> validate + reconcile + resume
```

Do not blindly roll back RAW. Prefer replay, idempotent rerun, backfill, Time Travel, UNDROP, clone recovery, affected-window rebuild and deterministic SCD2 history rebuild over manual PROD DML.

## 19. Data quality, reconciliation and freshness

Baseline DQ:

- not-null;
- uniqueness;
- relationships;
- accepted values;
- domain assertions;
- volume checks;
- SCD2 invariants;
- schema contracts;
- reconciliation.

Reconciliation may include row counts, distinct business-key counts, control totals, min/max timestamps, watermarks, rejected rows and duplicates.

Track separately:

1. source freshness;
2. pipeline freshness / processed watermark;
3. published dataset freshness.

Pipeline success does not imply consumer readiness.

## 20. Observability and incident lifecycle

Start Snowflake-native: account usage, query/warehouse history, dbt artifacts, GitHub Actions and account-local `PLATFORM_CONTROL`.

Incident lifecycle:

```text
DETECT -> TRIAGE -> CONTAIN -> RECOVER -> RECONCILE -> VALIDATE -> RESUME -> CLOSE
```

Do not build a custom ITSM system.

## 21. Cost attribution

Do not use database-per-source as the primary chargeback model.

```text
Domain storage/recovery       -> domain database
Source/table storage detail   -> schema/table metrics
Compute                       -> domain/workload warehouse + query tags
Serverless ingestion/services -> Snowflake service usage history
```

Structured query tags should eventually carry domain/source/pipeline/dataset/run/release metadata.

Cost monitors/budgets/tags remain Phase 1 hardening after live administrative boundaries are verified.

## 22. Semantic Views

Use Snowflake-native Semantic Views; Cube is excluded. Semantic definitions participate in project release/regression lifecycle where practical.

## 23. New-domain onboarding

A future Finance domain should primarily add metadata/contracts/domain SQL/tests/semantic definitions and source-specific ingestion config.

Platform onboarding derives standard resources:

```text
DEV_FINANCE
CI_FINANCE
UAT_FINANCE
PROD_FINANCE

AR_FINANCE_GUEST
AR_FINANCE_READER
AR_FINANCE_DEVELOPER
AR_FINANCE_ADMIN

DR_FINANCE_ANALYTICS_GUEST/READ/WRITE/OWNER

WH_FINANCE_QUERY
WH_FINANCE_TRANSFORM
WH_FINANCE_CI
```

Employee membership then flows through IdP/SCIM rather than per-user Terraform changes.

Adding another physical Finance source normally adds source metadata/RAW structures, not another environment database or bespoke RBAC framework.

## 24. Implementation roadmap

- **Phase 0 — Architecture:** complete.
- **Phase 1 — Platform Foundation:** **in progress**; static organization/account/domain-RBAC/warehouse/state-adapter/WIF foundation is implemented; real remote state, Snowflake bootstrap/apply, schema lifecycle and cost hardening remain.
- **Phase 2 — Framework Foundation:** metadata validation, dbt package, environment macros, basic loads, reusable CI, operational logging.
- **Phase 3 — Thin CI/CD spine:** DEV -> PR CI -> UAT -> PROD with exact SHA, history/recovery point/cleanup/rollback skeleton.
- **Phase 4 — Health vertical slice:** deterministic Health RAW -> semantic with contracts/DQ/reconciliation/freshness/recovery/SCD2.
- **Phase 5 — Transport streaming:** direct Snowpipe Streaming then Kafka Connector using the same RAW event contract.
- **Phase 6 — Pattern catalog:** approved load/SCD2 patterns, late data/dedup/replay/backfill/schema evolution.
- **Phase 7 — Production hardening:** masking/RAP/classification/cost/drift/health views/alerts/recovery drills/SLO reporting.
- **Phase 8 — Openflow:** SQL Server -> Openflow CDC -> Health RAW without downstream redesign.

## 25. Current Phase 1 implementation status

Completed in source/static CI:

- [x] Terraform CLI `1.16.0` and Snowflake provider `2.19.0` pinned.
- [x] committed provider lock files for all seven roots.
- [x] three-account DEV/UAT/PROD design.
- [x] organization Terraform root with ORGADMIN isolation.
- [x] per-account identity roots and Snowflake GitHub OIDC WIF service-user configuration.
- [x] dedicated routine `AR_TERRAFORM_<ENV>` roles.
- [x] environment × domain databases.
- [x] domain GUEST/READER/DEVELOPER/ADMIN account roles.
- [x] domain GUEST/READ/WRITE/OWNER database roles.
- [x] GUEST limited to MARTS/SEMANTIC and no CI database access.
- [x] per-domain QUERY/TRANSFORM warehouses and DEV CI warehouses.
- [x] backend-independent Terraform roots.
- [x] Azure Blob backend profile.
- [x] S3 backend profile with native lockfile.
- [x] runtime backend selector.
- [x] static CI for seven roots and both backend declarations.
- [x] manual DEV plan workflow supporting Azure Blob or S3 state + Snowflake WIF.
- [x] employee-membership boundary documented as IdP/SCIM, not Terraform user grants.
- [x] `docs/CURRENT_CONTEXT.md` fast handoff entrypoint.

Still required before Phase 1 exit:

- [ ] provision one real remote-state control plane: Azure Blob **or** S3;
- [ ] configure the matching GitHub OIDC trust/permissions;
- [ ] securely execute/import Snowflake organization accounts;
- [ ] apply DEV identity bootstrap against a live Snowflake account;
- [ ] configure GitHub Environment `dev`;
- [ ] run/review the first real DEV remote plan;
- [ ] apply DEV under review and verify effective privileges/objects in Snowflake;
- [ ] implement personal DEV and PR CI schema lifecycle outside long-lived platform state;
- [ ] add query-tag/cost-control/resource-monitor baseline where supported;
- [ ] prove UAT before protected PROD automation.

## 26. ADR index

| ADR | Decision | Status |
|---|---|---|
| ADR-001 | five-repository architecture | Accepted |
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
| ADR-022 | S3-only remote-state reference | Superseded by ADR-024 |
| ADR-023 | GitHub OIDC Terraform identity | Accepted |
| ADR-024 | Azure Blob/S3 backend adapter model | Accepted |

## 27. Immediate next step

Do not start Kafka, Snowpipe Streaming, Openflow or broad dbt modelling yet.

Next execution order:

```text
choose/provision one real remote-state backend
-> Snowflake organization bootstrap/import
-> DEV identity bootstrap
-> configure GitHub Environment dev
-> first real DEV remote plan
-> reviewed DEV apply
-> Snowflake-side verification
-> personal/PR schema lifecycle + cost baseline
-> UAT proof
-> protected PROD path
```
