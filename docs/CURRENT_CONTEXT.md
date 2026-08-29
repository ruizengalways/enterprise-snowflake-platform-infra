# Enterprise Snowflake Platform — Current Context

> **Purpose:** Fast handoff for a new conversation/session. Read this file first, then `PROJECT_BLUEPRINT.md` for long-term architecture.
>
> **Updated:** 2026-08-29
>
> **Current phase:** Phase 1 platform foundation + early framework foundation. Source/static CI is increasingly complete; no live Snowflake apply has happened yet.

## 1. Core rules

- Common technical behaviour is metadata-driven; genuine domain/business logic stays explicit SQL/code.
- Do not create a YAML programming language.
- No DEV/UAT/PROD Git branches; promote immutable Git SHA.
- One Snowflake object has one authoritative lifecycle owner.
- Git is configuration source of truth; `PLATFORM_CONTROL` is runtime/operational state.
- Human identity and machine identity are separate.
- Terraform defines stable roles/privileges/warehouses; Entra ID / Okta / SCIM controls employee membership.
- Recoverability, reconciliation, freshness, observability and cost attribution are first-class.
- Do not start Kafka, Snowpipe Streaming or Openflow before platform/framework foundations are proven.

## 2. Repositories and ownership

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

- **platform-infra** — accounts/platform Terraform, RBAC, warehouses, state/WIF, workspace access, cost/governance/control-plane foundation.
- **data-project-framework** — metadata schemas/validation, workspace/query-tag utilities, dbt target resolution, metadata→dbt bridge, basic standard load configuration, reusable CI/workflows.
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

CI is not a fourth account.

Database = environment × governed domain, not physical source.

Stable schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Published schemas initially: `MARTS`, `SEMANTIC`. RAW source-purpose schemas appear only when a real source is onboarded.

## 4. Human RBAC / employee membership

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

Employee changes are IdP/SCIM operations, not Terraform user changes:

```text
Employee / contractor
  -> Entra ID / Okta group
  -> SCIM / approved provisioning
  -> AR_<DOMAIN>_<CAPABILITY>
```

## 5. Domain compute

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV account only
WH_PLATFORM_OPS
```

Environment project metadata declares query/transform/CI warehouse keys. Root Terraform derives grants from metadata; new domains do not require copied Health/Transport grant blocks.

## 6. DEV personal + PR workspaces

Human roles attach to `DEV_<DOMAIN>`, never `CI_<DOMAIN>`.

DEV WRITE gets `CREATE SCHEMA` on its DEV database.

Personal convention:

```text
<DEVELOPER>_<LAYER>
```

This is a namespace convention, not a per-person security boundary.

Machine-only CI capability:

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> USAGE + CREATE SCHEMA on CI_<DOMAIN>
  -> USAGE on WH_<DOMAIN>_CI
```

PR convention:

```text
PR_<NUMBER>_<LAYER>
```

Framework PR schemas are transient with zero-day Time Travel and prefix-guarded cleanup.

## 7. Project CI identities

Lifecycle:

```text
identity/dev
  -> platform/dev
      -> project-identity/dev
```

`terraform/stacks/project-identity/dev/` uses generic `service-identity` and grants no account-level privileges.

```text
SU_GITHUB_HEALTH_CI
  -> AR_HEALTH_CI
  -> repo:ruizengalways/enterprise-snowflake-health-analytics:environment:ci

SU_GITHUB_TRANSPORT_CI
  -> AR_TRANSPORT_CI
  -> repo:ruizengalways/enterprise-snowflake-transport-analytics:environment:ci
```

Source is statically validated; no live apply yet. See ADR-027.

## 8. Terraform lifecycle/state

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

Platform Terraform WIF:

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Routine privileges:

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

## 9. Remote Terraform state

Snowflake is not AWS-dependent.

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

Runtime adapter:

```text
terraform/backend-profiles/azurerm/backend.tf
terraform/backend-profiles/s3/backend.tf
terraform/scripts/select-backend.sh
```

OneDrive/SharePoint may hold docs/runbooks/audit evidence, not live Terraform state. One deployment chooses one writable backend.

## 10. Framework executable baseline

```text
src/enterprise_snowflake_framework/
├── workspaces.py
├── query_tags.py
├── metadata_validation.py
├── targets.py
└── dbt_vars.py

project_schema/
├── project.schema.json
├── dataset.schema.json
└── raw_contract.schema.json

scripts/
├── render_workspace_sql.py
├── render_query_tag.py
├── resolve_dbt_target.py
├── render_dbt_vars.py
└── assert_dbt_manifest.py

dbt_package/
├── dbt_project.yml
└── macros/
    ├── environment/targets.sql
    └── loading/strategies.sql

.github/actions/
├── validate-metadata/action.yml
└── dbt-static-check/action.yml

.github/workflows/
├── framework-ci.yml
└── pr-workspace.yml
```

## 11. Metadata contracts

Version 1 validates project, dataset and project-owned RAW-contract metadata.

Dataset technical metadata:

```text
raw_contract
load_strategy
implementation
business_key
watermark_column
freshness
reconciliation
```

RAW contracts include source/entity/grain/key, columns/types/nullability/classification, source timestamp, snapshot/append/CDC semantics, cadence, retention and breaking-change policy.

Cross-file validation checks references, duplicate IDs/columns, keyed-strategy keys, freshness order, declared timestamp/key columns and CDC operation/sequence columns.

Metadata does **not** contain business joins, formulas, arbitrary SQL or workflow branching.

See ADR-028.

## 12. Current domain contracts

### Health `patient`

```text
source_system:       ehr_mssql
load_strategy:       scd2_snapshot
business_key:        patient_id
watermark:           source_updated_at
change semantics:    CDC + tombstone delete
freshness:           warn 60 min / error 120 min
contract policy:     versioned_contract
```

### Transport `vehicle_position`

```text
source_system:       gtfs_realtime
load_strategy:       append_only
RAW identity field:  vehicle_id
watermark:           event_timestamp
change semantics:    append
freshness:           warn 5 min / error 15 min
contract policy:     versioned_contract
```

Transport ingestion technology remains deferred; future direct Snowpipe Streaming and Kafka Connector paths must converge on this logical RAW contract.

## 13. dbt physical target resolution

Canonical stable reference:

```text
dbt-core      1.12.3
dbt-snowflake 1.12.0
```

Resolver inputs:

```text
project_code
environment = dev | ci | uat | prod
workload    = query | transform | ci
optional developer for DEV personal workspace
optional PR number for CI
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

Examples:

```text
HEALTH + dev + transform + alice.smith
 -> DEV_HEALTH / WH_HEALTH_TRANSFORM / ALICE_SMITH_<LAYER>

HEALTH + ci + ci + PR 123
 -> CI_HEALTH / WH_HEALTH_CI / PR_123_<LAYER>

TRANSPORT + uat + transform
 -> UAT_TRANSPORT / WH_TRANSPORT_TRANSFORM / <LAYER>
```

Root project macros explicitly delegate database/schema naming to the framework package. Model SQL should use `ref()` / `source()` and never hard-code DEV/UAT/PROD physical databases.

Profiles contain no passwords/private keys. Human DEV defaults to external-browser auth; machine targets use Snowflake `workload_identity`, provider `OIDC`, and a short-lived token.

See ADR-029.

## 14. Metadata → dbt bridge

`render_dbt_vars.py` validates the project tree first and exposes only bounded technical metadata:

```text
esf_project
esf_datasets
```

The reusable `dbt-static-check` action now:

```text
install pinned framework + dbt
-> resolve offline CI target
-> validate/render project metadata into dbt vars
-> dbt deps
-> dbt parse --vars <validated vars>
```

Therefore a metadata change that affects materialization is tested together with the checked-in dbt package/profile/macros.

## 15. Basic metadata-driven load strategies — implemented and CI-proven

A standard project model can declare only its governed dataset ID:

```jinja
{{ enterprise_snowflake_framework.esf_configure_dataset('vehicle_position') }}
```

The project still writes explicit SQL. Framework reads validated dataset metadata and configures:

```text
full_refresh
  -> materialized=table

append_only
  -> materialized=incremental
  -> incremental_strategy=append

incremental_merge
  -> materialized=incremental
  -> incremental_strategy=merge
  -> unique_key from dataset.business_key
```

Composite keys remain composite.

Important boundary: `append_only` does **not** invent a source/checkpoint predicate. The rows selected by the model during an incremental invocation are the rows appended. Source/watermark filtering stays explicit until a separately approved common checkpoint primitive exists.

The basic macro deliberately fails for:

```text
implementation: custom
scd2_snapshot
scd2_merge
scd2_stream_task
```

Custom logic stays project-owned; SCD2 requires dedicated implementations and invariant tests.

See ADR-030.

## 16. Framework revision alignment

Health and Transport now use one aligned immutable framework revision for metadata action, dbt package, dbt static action and PR workspace workflow:

```text
3408025d4280d57c3bbed0c295e1686fa7d950ea
```

This prevents hidden drift where different shared capabilities point at unrelated framework commits.

## 17. Reusable PR workspace workflow

Thin project callers invoke the pinned framework workflow.

```text
PR opened/reopened/synchronize -> create PR_<n>_* schemas
PR closed                      -> drop only PR_<n>_* schemas
```

The workflow targets GitHub Environment `ci`, requests a GitHub OIDC token with an account-scoped Snowflake audience, authenticates as the project CI service identity and executes framework-generated workspace SQL only. It does not currently run arbitrary PR business code while holding Snowflake credentials.

No live project-CI identity/GitHub Environment exists yet, so no real PR schema has been created.

## 18. Query tag + cost attribution

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

See ADR-026.

## 19. Verified CI

### Platform Terraform

```text
Run:    33223588208
Commit: 509f2986dd9b74f063e7f65b4dfcf8d7655cf5ed
Result: SUCCESS
```

Includes organization, identity/dev|uat|prod, dev, project-identity/dev, uat, prod, fmt, Azure backend and S3 backend validation.

### Framework basic-load proof

```text
Run:    33234967048
Commit: 3408025d4280d57c3bbed0c295e1686fa7d950ea
Result: SUCCESS
```

Both jobs succeeded. The dbt job proves:

```text
target -> CI_HEALTH.PR_123_STAGING
full_refresh -> table
append_only -> incremental + append
incremental_merge -> incremental + merge + unique_key=id
```

### Health aligned project CI

```text
Metadata CI:   33235029796  SUCCESS
dbt Static CI: 33235034461  SUCCESS
```

### Transport aligned project CI

```text
Metadata CI:   33235050367  SUCCESS
dbt Static CI: 33235056338  SUCCESS
```

Static CI proves source/schema/package/macro/config validity, not live Snowflake authorization or runtime data correctness.

## 20. What has NOT happened yet

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
- no generic source checkpoint/watermark predicate yet;
- no reconciliation/freshness/audit runtime primitives yet;
- no SCD2 framework implementation yet;
- no UAT/PROD project deployment identities/workflows yet;
- no persisted cost views/resource monitors/budgets;
- no Health/Transport business models yet;
- Kafka Connector, Snowpipe Streaming and Openflow remain deferred.

## 21. Next useful source work

Without live accounts, the next highest-value sequence is:

```text
1. integrate canonical QUERY_TAG into dbt invocation/model lifecycle
2. implement reconciliation/freshness/audit primitives
3. design explicit checkpoint/watermark helper without hiding source semantics
4. implement dedicated SCD2 snapshot/merge/stream-task patterns + invariants
5. define DEV deployment and UAT/PROD promotion identity/workflow contracts
```

When real infrastructure becomes available:

```text
choose Azure Blob OR S3
-> provision state/OIDC
-> organization bootstrap/import
-> identity/dev apply
-> platform/dev plan/apply/verify
-> project-identity/dev apply
-> configure GitHub Environment ci
-> real PR workspace create/drop
-> live dbt/basic-load smoke test
-> UAT
-> protected PROD
```

## 22. Important ADRs

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
```
