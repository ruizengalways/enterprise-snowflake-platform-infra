# Enterprise Snowflake Platform — Project Blueprint

> **Status:** Phase 1 in progress — static platform/workspace/cost foundations implemented; real remote state + Snowflake DEV plan/apply remain
>
> **Authority:** Canonical long-term architecture for the Enterprise Snowflake Platform.
>
> **Fast handoff:** Read [`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) first in a new conversation/session.

## 1. Goal

Build a production-grade reusable Snowflake platform reference implementation suitable for real enterprise adoption and senior/principal platform/data engineering work.

Key outcomes:

- clear platform/domain ownership;
- repeatable domain/source onboarding;
- stable RAW contracts independent of ingestion technology;
- metadata-driven common technical behaviour without hiding business logic;
- immutable Git SHA promotion;
- DEV/UAT/PROD account isolation;
- least-privilege human and machine identity;
- recoverability, reconciliation, freshness/SLOs, observability and cost attribution;
- multiple approved implementation patterns where workloads genuinely differ.

## 2. Non-goals

- do not merge Metric Guard into this project;
- do not maximise technology count for appearance;
- do not Terraform-manage every Snowflake object;
- do not turn YAML into a programming language;
- do not use DEV/UAT/PROD Git branches;
- do not use Dynamic Tables for SCD2;
- do not introduce Spark Streaming without a concrete requirement;
- Marketplace Secure Shares are not a replacement for ingestion;
- do not build a custom ITSM system.

## 3. Architecture principles

1. Convention over copy/paste.
2. Configuration for stable technical behaviour; explicit code for real business differences.
3. Domain autonomy inside platform guardrails.
4. RAW contracts isolate ingestion technology from downstream engineering.
5. Promote the same immutable Git SHA across environments.
6. Human identity and machine deployment identity are separate.
7. Production readiness includes recovery/reconciliation, not deployment success alone.
8. One Snowflake object has one authoritative lifecycle owner.
9. Git is configuration source of truth; `PLATFORM_CONTROL` stores runtime/operational state.
10. Prefer deterministic replay/rebuild over manual PROD DML.
11. Account, database, schema and warehouse boundaries solve different problems.
12. Cost attribution is multi-dimensional; database-per-source is not a chargeback strategy.
13. Consumer access is narrower than engineering access.
14. Bootstrap identity/state is separated from routine automation that consumes it.
15. Avoid long-lived CI credentials when federation is available.
16. Personal DEV schema names are namespaces, not fake security boundaries.

## 4. Repository architecture

| Repository | Responsibility |
|---|---|
| `enterprise-snowflake-platform-infra` | accounts/platform Terraform, RBAC, warehouses, state/WIF, governance/control/cost/recovery foundations |
| `enterprise-snowflake-data-project-framework` | versioned dbt/shared technical mechanics, metadata validation, workspace/query-tag utilities, reusable delivery/recovery workflows |
| `enterprise-snowflake-demo-source-systems` | deterministic external source/event simulation only |
| `enterprise-snowflake-health-analytics` | Health contracts/config/business SQL/tests/semantic/ingestion config |
| `enterprise-snowflake-transport-analytics` | Transport contracts/config/business SQL/tests/semantic/streaming config |

Projects stay thin and consume pinned framework versions. Shared technical fixes should not require copy/paste edits in every project repo.

## 5. Snowflake account topology

```text
Snowflake Organization
│
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

CI is not a fourth account. PR CI uses separate `CI_<DOMAIN>` databases and `WH_<DOMAIN>_CI` warehouses inside DEV.

See ADR-018.

## 6. Database and schema boundary

Analytics database pattern:

```text
<ENVIRONMENT>_<DOMAIN>
```

A database represents environment × governed data product/domain, not a physical MSSQL/MySQL/API/file/stream source.

Stable transformation schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Published consumer schemas initially:

```text
MARTS
SEMANTIC
```

Source-purpose RAW schemas are created only when a real source is onboarded, e.g. `RAW_EHR_MSSQL` or `RAW_INSURANCE_API`.

See ADR-019.

## 7. Human RBAC and employee identity

Per-domain human account roles:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

Stable domain database roles:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
  -> DR_<DOMAIN>_ANALYTICS_READ
  -> DR_<DOMAIN>_ANALYTICS_WRITE
  -> DR_<DOMAIN>_ANALYTICS_OWNER
```

Policy:

- GUEST sees published MARTS/SEMANTIC only;
- READER sees all stable layers;
- DEV DEVELOPER receives WRITE;
- UAT/PROD DEVELOPER is read-only by default;
- UAT/PROD ADMIN currently receives transform compute as a transitional path;
- Health role membership never implies Transport access.

Terraform owns the role/privilege model, not employee records.

Target enterprise membership flow:

```text
Employee/contractor
  -> Entra ID / Okta group
      -> SCIM / approved identity provisioning
          -> AR_<DOMAIN>_<CAPABILITY>
```

Adding/removing an employee from an existing domain should not require Terraform.

See ADR-020 and `architecture/RBAC_MODEL.md`.

## 8. Domain compute

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
WH_PLATFORM_OPS
```

Account identifies environment; warehouse identifies domain + workload.

Environment project metadata carries query/transform/CI warehouse keys, and root Terraform derives grants from metadata. New domains should not require copying Health/Transport-specific grant blocks.

Baseline warehouse defaults remain conservative: XSMALL, auto-resume, 60-second auto-suspend, initially suspended, explicit statement timeout, no multi-cluster/query acceleration without evidence.

## 9. DEV personal workspaces

Human domain RBAC in DEV attaches only to `DEV_<DOMAIN>` databases.

DEV domain WRITE receives `CREATE SCHEMA` on the corresponding DEV database.

Personal schema convention:

```text
<DEVELOPER>_<LAYER>
```

Example:

```text
DEV_HEALTH.ALICE_SMITH_STAGING
```

This is a developer namespace, not per-person access isolation. If a real enterprise requires stronger isolation, add identity-governed personal roles rather than relying on a prefix.

## 10. PR CI workspaces

Human domain roles do not attach to `CI_<DOMAIN>`.

DEV creates machine-only roles:

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> USAGE + CREATE SCHEMA on CI_<DOMAIN>
  -> USAGE on WH_<DOMAIN>_CI
```

PR schema pattern:

```text
PR_<NUMBER>_<LAYER>
```

The framework owns deterministic naming, identifier validation and guarded create/drop SQL. PR workspaces are transient with zero-day Time Travel and are explicitly removed by PR lifecycle automation.

A GitHub OIDC project-CI service user that receives `AR_<DOMAIN>_CI` remains to be implemented.

See ADR-025.

## 11. Terraform ownership and roots

Terraform owns selected stable platform infrastructure/RBAC, not dbt business relations.

Current roots:

```text
terraform/stacks/organization/
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

`organization/` alone uses ORGADMIN for account lifecycle.

`identity/<env>/` bootstraps platform Terraform service users/WIF and dedicated machine roles under exceptional ACCOUNTADMIN authority.

Routine `dev/uat/prod` roots activate only:

```text
AR_TERRAFORM_DEV
AR_TERRAFORM_UAT
AR_TERRAFORM_PROD
```

Initial routine privileges:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Current reusable modules:

```text
analytics-environment
warehouse
platform-control
rbac
workspace-access
workload-identity
```

Terraform `1.16.0` and `snowflakedb/snowflake` provider `2.19.0` are pinned; every root commits `.terraform.lock.hcl`.

## 12. Remote Terraform state

The Snowflake platform is not AWS-dependent.

Supported profiles:

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

Terraform backend type is selected at execution time using:

```text
terraform/backend-profiles/azurerm/backend.tf
terraform/backend-profiles/s3/backend.tf
terraform/scripts/select-backend.sh
```

The selector materialises ignored `backend.generated.tf` before remote `terraform init`.

Microsoft reference:

```text
GitHub OIDC -> Entra workload federation -> Azure Blob state
```

AWS reference:

```text
GitHub OIDC -> AWS IAM -> S3 state + native .tflock
```

OneDrive/SharePoint may store docs/runbooks/approvals/evidence, not authoritative live Terraform state.

One deployment chooses one writable backend for each state. Backend migration is controlled; S3 and Azure Blob are not dual writers.

See ADR-024.

## 13. Platform Terraform WIF

```text
GitHub Environment dev  -> SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
GitHub Environment uat  -> SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
GitHub Environment prod -> SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

OIDC subject is repository + GitHub Environment scoped. Audience is account-scoped; the shared `snowflakecomputing.com` audience is intentionally rejected for these identities.

No routine Snowflake password/private key is stored.

See ADR-023.

## 14. Data project framework

The framework is a versioned dependency, not a copied folder.

First executable slice now exists:

```text
src/enterprise_snowflake_framework/workspaces.py
src/enterprise_snowflake_framework/query_tags.py
scripts/render_workspace_sql.py
scripts/render_query_tag.py
tests/
.github/workflows/framework-ci.yml
```

Workspace utilities render personal/PR names and guarded SQL.

Query-tag utilities render deterministic compact JSON and optional:

```sql
ALTER SESSION SET QUERY_TAG = '<json>';
```

Required query-tag fields:

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

Do not place personal/sensitive/regulated/business payload data in query tags.

Next framework layers will add metadata schemas/validation, dbt environment resolution, approved load/SCD2 strategies, reconciliation/freshness/audit and reusable delivery/recovery workflows.

## 15. Metadata-driven design

Metadata may configure stable technical behaviour such as:

```text
strategy
key / composite key
source relation
watermark/timestamp
tracked columns
delete/dedup policy
freshness/reconciliation thresholds
criticality/recovery targets
warehouse binding
```

Business joins, calculations and domain rules stay explicit SQL/code.

Escape hatch:

```yaml
implementation: custom
```

Custom implementations still participate in standard contracts, testing, observability, reconciliation and recovery.

## 16. RAW contract boundary

Project-owned RAW contracts define the ingestion/downstream interface: source, owner, schema version, grain, business key, required columns/types/nullability, source timestamp, CDC semantics, sequence/offset, cadence, retention, classification and breaking-change policy.

Typical technical columns:

```text
source_operation
source_sequence
source_updated_at
ingested_at
batch_id
source_system
```

Ingestion technology can change without forcing downstream redesign.

## 17. Ingestion patterns

All paths converge on project RAW contracts:

```text
Synthetic/file/database source ─┐
Snowpipe Streaming             ─┼─> RAW -> downstream dbt
Kafka Connector                ─┤
Openflow CDC                   ─┘
```

Transport later compares direct Snowpipe Streaming and Kafka Connector against the same logical event contract. Health adds Openflow only after the downstream pipeline is proven.

## 18. dbt and SCD2 architecture

Transformation flow:

```text
RAW -> staging -> intermediate/canonical -> marts -> semantic
```

Model SQL must not hard-code physical DEV/UAT/PROD names.

Approved load strategies:

```text
full_refresh
append_only
incremental_merge
scd2_snapshot
scd2_merge
scd2_stream_task
```

Dynamic Tables are not an approved SCD2 mechanism.

SCD2 tests must cover unchanged/changed rows, composite keys, duplicates, multiple changes, late/out-of-order data, deletes, idempotency, backfill and deterministic rebuild.

## 19. CI/CD and release promotion

Project delivery target:

```text
feature branch
-> personal/shared DEV
-> PR CI in CI_<DOMAIN>
-> merge
-> UAT
-> approval
-> PROD
-> smoke + DQ + reconciliation
```

Promote the same immutable Git SHA; do not use environment branches.

PR close removes PR workspaces.

Platform-infra progression:

```text
static CI
-> organization bootstrap/import
-> DEV Terraform identity bootstrap
-> manual DEV remote plan
-> reviewed/protected DEV apply
-> UAT
-> protected PROD
```

`terraform-plan-dev.yml` is manual-only and does not apply.

## 20. Rollback and recovery

For derived analytics data:

```text
pre-release zero-copy clone
-> deploy
-> smoke/DQ/reconciliation
-> PASS: retain release
-> FAIL: controlled SWAP to known-good state
-> validate/reconcile/resume
```

Do not blindly roll back RAW.

Recovery catalog should include retry/checkpoint/replay/idempotent rerun/backfill/Time Travel/UNDROP/clone/rebuild. Prefer deterministic repair over manual PROD DML.

## 21. Data quality, reconciliation and freshness

Baseline DQ:

```text
not-null
uniqueness
relationships
accepted values
domain assertions
volume checks
SCD2 invariants
schema contracts
```

Reconciliation includes row counts, distinct business-key counts, control totals, min/max business timestamps, watermarks, rejects and duplicates.

Freshness is tracked separately as source freshness, pipeline/processed watermark and published dataset freshness.

Dataset readiness can require transformation + DQ + reconciliation + freshness + semantic regression.

## 22. Cost attribution

Do not use database-per-source as the primary chargeback mechanism.

Use complementary dimensions:

```text
Domain storage/recovery         -> <ENVIRONMENT>_<DOMAIN>
Compute                         -> WH_<DOMAIN>_<WORKLOAD>
Query execution                 -> QUERY_TAG + QUERY_ATTRIBUTION_HISTORY
Warehouse idle                  -> WAREHOUSE_METERING_HISTORY
Serverless/ingestion            -> service-specific usage history
Storage detail                  -> Snowflake storage history/metrics
```

`QUERY_ATTRIBUTION_HISTORY.CREDITS_ATTRIBUTED_COMPUTE` excludes warehouse idle time, so it is not the complete warehouse bill.

Baseline diagnostic SQL:

```text
snowflake/monitoring/queries/cost_attribution.sql
```

Persisted observability/cost views, resource monitors/budgets and exact invoice reconciliation remain later live-account hardening.

See ADR-026 and `standards/COST_ATTRIBUTION.md`.

## 23. Semantic layer

Use Snowflake-native Semantic Views; Cube is excluded. Semantic definitions participate in project release/regression lifecycle where practical.

## 24. New-domain onboarding target

For a future `FINANCE` domain the platform should derive:

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
CI_FINANCE.DR_FINANCE_CI_WORKSPACE

WH_FINANCE_QUERY
WH_FINANCE_TRANSFORM
WH_FINANCE_CI
```

The platform should require domain metadata/config and project code, not cloned Terraform logic. Employee growth from 5 to 500 people should not change Terraform membership records.

## 25. Roadmap

- **Phase 0 — Architecture:** complete.
- **Phase 1 — Platform Foundation:** in progress; static Terraform/state/WIF/domain RBAC/workspaces/query-tag/cost-query baseline implemented; live control plane + DEV apply/verification and project-CI identity remain.
- **Phase 2 — Framework Foundation:** metadata schemas/validation, dbt package/environment resolution, basic load patterns, reusable CI/audit/reconciliation/freshness.
- **Phase 3 — Thin CI/CD spine:** prove DEV -> PR CI -> UAT -> PROD with exact SHA and cleanup/recovery skeleton.
- **Phase 4 — Health vertical slice:** Health RAW -> semantic with contracts/DQ/reconciliation/recovery/SCD2.
- **Phase 5 — Transport streaming:** direct Snowpipe Streaming then Kafka Connector against same RAW event contract.
- **Phase 6 — Pattern catalog:** load/SCD2/late-data/dedup/replay/backfill/schema evolution.
- **Phase 7 — Production hardening:** governance, cost/drift, alerts, recovery drills, SLO reporting.
- **Phase 8 — Openflow:** SQL Server -> Openflow CDC -> Health RAW without downstream redesign.

## 26. Phase 1 source/static-CI status

Completed/proven in source or CI:

- [x] Terraform 1.16.0 + Snowflake provider 2.19.0 pinned.
- [x] Lock files committed; CI uses readonly dependency locks.
- [x] DEV/UAT/PROD + organization/identity/routine root separation.
- [x] Azure Blob and S3 backend adapters.
- [x] Platform Terraform GitHub OIDC/Snowflake WIF source implementation.
- [x] Environment × domain databases and stable schemas.
- [x] GUEST/READER/DEVELOPER/ADMIN human RBAC.
- [x] Metadata-driven domain warehouse grants.
- [x] DEV personal `CREATE SCHEMA` workspace capability.
- [x] Human roles removed from CI databases.
- [x] `AR_<DOMAIN>_CI` + `DR_<DOMAIN>_CI_WORKSPACE` + CI warehouse grants.
- [x] Framework workspace renderer + tests/CI.
- [x] Framework canonical query-tag builder + SQL renderer + tests/CI.
- [x] Snowflake-native cost attribution diagnostic queries.
- [x] Canonical handoff documentation in `CURRENT_CONTEXT.md`.

Still required before Phase 1 exit:

- [ ] provision one real Azure Blob or S3 state control plane + GitHub OIDC trust;
- [ ] bootstrap/import real Snowflake DEV/UAT/PROD accounts;
- [ ] apply `identity/dev` and prove WIF;
- [ ] run/review/apply real DEV Terraform and verify effective grants;
- [ ] implement project PR-CI OIDC service identities bound to `AR_<DOMAIN>_CI`;
- [ ] prove actual PR workspace create/cleanup against Snowflake;
- [ ] establish narrow live cost-history access and verify attribution queries;
- [ ] prove UAT, then protected PROD;
- [ ] add resource monitors/budgets/tagging hardening where actual administrative/edition boundaries permit.

## 27. ADR index

```text
ADR-001  five-repository architecture
ADR-003  capability account roles + database roles
ADR-004  selective Terraform / one object owner
ADR-006  metadata-driven technical behaviour
ADR-007  RAW contract boundary
ADR-017  shared apply requires remote state + workload identity
ADR-018  three-account topology
ADR-019  environment × domain database boundary
ADR-020  domain GUEST + workload warehouses
ADR-021  isolated ORGADMIN bootstrap
ADR-022  S3-only backend choice — superseded by ADR-024
ADR-023  GitHub OIDC Terraform identity
ADR-024  Azure Blob/S3 backend adapters
ADR-025  DEV personal + PR CI workspace lifecycle
ADR-026  query-tag + cost-attribution contract
```

## 28. Immediate next source work

While real cloud/Snowflake accounts are unavailable, continue with:

```text
1. project-CI identity contract / reusable PR workspace workflow
2. project metadata JSON Schema + validation
3. dbt environment/database/schema resolution primitives
4. thin reusable CI/CD spine contracts
```

Do not start Kafka, Snowpipe Streaming or Openflow before these foundations are proven.
