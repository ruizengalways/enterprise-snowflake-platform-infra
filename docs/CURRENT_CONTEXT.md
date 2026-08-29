# Enterprise Snowflake Platform — Current Context

> **Purpose:** Fast handoff for a new conversation/session. Read this file first, then `PROJECT_BLUEPRINT.md` for long-term architecture.
>
> **Updated:** 2026-08-29
>
> **Current phase:** Phase 1 platform foundation + early framework foundation. Source/static CI is progressing; no live Snowflake apply has happened yet.

## 1. Core rules

- Common technical behaviour is metadata-driven; genuine domain/business logic stays explicit SQL/code.
- Do not create a YAML programming language.
- No DEV/UAT/PROD Git branches; promote immutable Git SHA.
- One Snowflake object has one authoritative lifecycle owner.
- Git is configuration source of truth; `PLATFORM_CONTROL` is runtime/operational state.
- Human identity and machine identity are separate.
- Terraform defines stable platform roles/privileges; Entra ID / Okta / SCIM controls employee membership.
- Recoverability, reconciliation, freshness, observability and cost attribution are first-class.
- Do not start Kafka, Snowpipe Streaming or Openflow before platform/framework foundations are proven.

## 2. Repositories

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

Ownership:

- **platform-infra** — Snowflake accounts/platform Terraform, RBAC, warehouses, state/WIF, workspace access, cost/governance/control-plane foundation;
- **data-project-framework** — reusable metadata contracts/validation, workspace/query-tag utilities, dbt target resolution/package, reusable CI/workflows and future generic load/DQ/reconciliation mechanics;
- **demo-source-systems** — deterministic external-style source simulation only;
- **health/transport analytics** — domain RAW contracts/config/business SQL/tests/semantic/ingestion configuration.

Project repos stay thin and pin framework revisions deliberately.

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

Database = environment × governed domain, not physical source. Stable schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Published schemas initially: `MARTS`, `SEMANTIC`. RAW source-purpose schemas appear only when a real source is onboarded.

## 4. Human RBAC and employee membership

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
- domain authority never crosses into another domain unless explicitly granted.

Employee lifecycle:

```text
Employee / contractor
  -> Entra ID / Okta group
  -> SCIM / approved provisioning
  -> AR_<DOMAIN>_<CAPABILITY>
```

Adding/removing an employee from an existing domain must not require Terraform.

## 5. Warehouses

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV account only
WH_PLATFORM_OPS
```

Project metadata in each environment declares query/transform/CI warehouse keys. Root Terraform derives grants from metadata rather than hard-coding Health/Transport pairs.

## 6. DEV personal workspace

Human roles attach to `DEV_<DOMAIN>`, never `CI_<DOMAIN>`.

DEV WRITE receives `CREATE SCHEMA` on the matching DEV database.

```text
<DEVELOPER>_<LAYER>
```

Example: `DEV_HEALTH.ALICE_SMITH_STAGING`.

This is a namespace convention, **not** per-person security isolation. Strong personal isolation would require separate identity-governed personal roles.

## 7. PR CI workspace and machine role

Machine-only DEV capability:

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> USAGE + CREATE SCHEMA on CI_<DOMAIN>
  -> USAGE on WH_<DOMAIN>_CI
```

Current examples:

```text
AR_HEALTH_CI
AR_TRANSPORT_CI
```

PR schemas:

```text
PR_<NUMBER>_<LAYER>
```

Framework rendering creates transient PR schemas with zero-day Time Travel and prefix-guarded cleanup.

## 8. Project PR-CI Snowflake identities — implemented in source

Lifecycle ordering:

```text
identity/dev
  -> platform/dev
      -> project-identity/dev
```

`terraform/stacks/project-identity/dev/` uses generic `terraform/modules/service-identity/` to create a WIF service user and bind it to an already-existing CI role. It does not create/expand that role and grants no account-level privileges.

```text
SU_GITHUB_HEALTH_CI
  -> AR_HEALTH_CI
  -> repo:ruizengalways/enterprise-snowflake-health-analytics:environment:ci

SU_GITHUB_TRANSPORT_CI
  -> AR_TRANSPORT_CI
  -> repo:ruizengalways/enterprise-snowflake-transport-analytics:environment:ci
```

Both use the DEV account-scoped Snowflake OIDC audience. Service users use `prevent_destroy`.

This root is statically Terraform-validated but has not been applied to live Snowflake.

See ADR-027.

## 9. Terraform lifecycle/state boundaries

Eight independent roots/state objects:

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

Source roots:

```text
terraform/stacks/organization/
terraform/stacks/identity/{dev,uat,prod}/
terraform/stacks/dev/
terraform/stacks/project-identity/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

State key added for project identity:

```text
enterprise-snowflake-platform-infra/project-identity/dev/terraform.tfstate
```

Platform Terraform identities:

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

Routine Terraform does not activate ACCOUNTADMIN/SYSADMIN/SECURITYADMIN. Identity bootstrap may use ACCOUNTADMIN only for machine-identity establishment. Organization root alone uses ORGADMIN.

Versions:

```text
Terraform CLI                 1.16.0
Snowflake Terraform provider  2.19.0
```

## 10. Remote Terraform state

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

OneDrive/SharePoint may store docs/runbooks/audit evidence, not authoritative live Terraform state. One deployment chooses one writable backend.

## 11. Framework executable baseline

Current framework code includes:

```text
src/enterprise_snowflake_framework/
├── workspaces.py
├── query_tags.py
├── metadata_validation.py
└── targets.py

project_schema/
├── project.schema.json
├── dataset.schema.json
└── raw_contract.schema.json

validation/validate_metadata.py
scripts/
├── render_workspace_sql.py
├── render_query_tag.py
├── resolve_dbt_target.py
└── assert_dbt_manifest.py

dbt_package/
├── dbt_project.yml
└── macros/environment/targets.sql

.github/actions/
├── validate-metadata/action.yml
└── dbt-static-check/action.yml

.github/workflows/
├── framework-ci.yml
└── pr-workspace.yml
```

Framework Python dependencies remain deliberately small (`PyYAML`, `jsonschema`) outside the dbt execution dependency set.

## 12. Project/dataset/RAW metadata contracts

Version 1 schemas validate:

```text
project
  code / name / repository / owner_team

dataset
  raw_contract / load_strategy / implementation
  business_key / watermark / freshness / reconciliation

RAW contract
  source_system / entity / grain / business_key
  columns/types/nullability/classification
  source_timestamp / snapshot|append|cdc semantics
  cadence / retention / breaking_change_policy
```

Semantic checks include duplicate dataset IDs/columns, RAW contract reference containment/existence, keyed-strategy business keys, freshness threshold order, declared business/source timestamp columns, and required CDC operation/sequence columns.

Metadata deliberately does **not** encode business joins, calculations, arbitrary SQL or workflow branching.

Reusable action:

```text
enterprise-snowflake-data-project-framework/.github/actions/validate-metadata/action.yml
```

Health and Transport now both invoke it from thin project workflows pinned to framework commit `01ce2fe9fcba3e5084297120703301f0dea4df1a`.

See ADR-028.

## 13. Current domain metadata baselines

### Health

First dataset:

```text
patient
source_system:       ehr_mssql
load_strategy:       scd2_snapshot
business_key:        patient_id
watermark:           source_updated_at
change semantics:    CDC + tombstone delete
freshness:           warn 60 min / error 120 min
contract policy:     versioned_contract
```

Files:

```text
health-analytics/config/project.yml
health-analytics/config/datasets/patient.yml
health-analytics/contracts/raw/patient.yml
```

### Transport

First dataset:

```text
vehicle_position
source_system:       gtfs_realtime
load_strategy:       append_only
RAW identity field:  vehicle_id
watermark:           event_timestamp
change semantics:    append
freshness:           warn 5 min / error 15 min
contract policy:     versioned_contract
```

Files:

```text
transport-analytics/config/project.yml
transport-analytics/config/datasets/vehicle_position.yml
transport-analytics/contracts/raw/vehicle_position.yml
```

Kafka/Snowpipe Streaming are still deferred; this contract exists so either future ingestion path can converge on the same downstream boundary.

## 14. dbt physical target resolution — implemented and CI-proven

Canonical reference versions:

```text
dbt-core      1.12.3
dbt-snowflake 1.12.0
```

The framework Python resolver is authoritative for environment routing. Inputs are deliberately small:

```text
project_code
environment = dev | ci | uat | prod
workload    = query | transform | ci
optional developer identity for DEV personal workspace
optional PR number for CI
```

It resolves:

```text
ESF_PROJECT_CODE
ESF_ENVIRONMENT
ESF_SCHEMA_PREFIX
DBT_DATABASE
DBT_WAREHOUSE
DBT_DEFAULT_SCHEMA
```

Canonical examples:

```text
HEALTH + dev + transform + alice.smith
 -> DEV_HEALTH
 -> WH_HEALTH_TRANSFORM
 -> ALICE_SMITH_<LAYER>

HEALTH + ci + ci + PR 123
 -> CI_HEALTH
 -> WH_HEALTH_CI
 -> PR_123_<LAYER>

TRANSPORT + uat + transform
 -> UAT_TRANSPORT
 -> WH_TRANSPORT_TRANSFORM
 -> stable <LAYER> schema

HEALTH + prod + query
 -> PROD_HEALTH
 -> WH_HEALTH_QUERY
 -> stable <LAYER> schema
```

The framework dbt package provides:

```text
esf_generate_database_name
esf_generate_schema_name
```

Each domain root keeps explicit thin wrapper macros that delegate to these package macros. Model SQL should use `ref()` / `source()` and must not hard-code physical DEV/UAT/PROD database names.

Health/Transport `profiles.yml` files contain no password/private key. Human DEV defaults to external-browser authentication. Machine profiles use Snowflake workload identity with `workload_identity_provider: OIDC` and a short-lived token supplied near execution.

Domain dbt packages pin framework revision `01ce2fe9fcba3e5084297120703301f0dea4df1a` and do not follow framework `main` implicitly.

Reusable static validation action:

```text
.github/actions/dbt-static-check/action.yml
```

It installs pinned dbt versions, resolves an offline CI target, installs packages and runs `dbt parse` without connecting to Snowflake.

Framework CI goes further: it inspects `manifest.json` and proves the smoke model resolves to `CI_HEALTH.PR_123_STAGING`.

See ADR-029.

## 15. Reusable PR workspace workflow

Framework:

```text
.github/workflows/pr-workspace.yml
```

Thin callers:

```text
health-analytics/.github/workflows/pr-workspace.yml
transport-analytics/.github/workflows/pr-workspace.yml
```

Both currently pin framework commit:

```text
7ffafbc83ec7da154f036613541bf34b8a913e1a
```

Lifecycle:

```text
PR opened/reopened/synchronize -> create idempotent PR_<n>_* workspace
PR closed                      -> drop only PR_<n>_* workspace
```

The workflow targets GitHub Environment `ci`, renders QUERY_TAG/workspace SQL, installs Snowflake CLI, manually requests an account-scoped GitHub OIDC token, authenticates as the project CI service identity and executes only framework-generated workspace SQL. It does not currently execute arbitrary PR business code while holding Snowflake credentials.

No live project-CI identity/GitHub Environment exists yet, so no real PR schema has been created.

## 16. Query-tag and cost attribution baseline

Query-tag required keys:

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

Do not include personal/secret/regulated/business payload data.

Cost model:

```text
Domain storage/recovery         -> <ENVIRONMENT>_<DOMAIN>
Compute                         -> WH_<DOMAIN>_<WORKLOAD>
Per-query execution attribution -> QUERY_TAG + QUERY_ATTRIBUTION_HISTORY
Warehouse idle compute          -> WAREHOUSE_METERING_HISTORY
Serverless/ingestion            -> service-specific usage histories
Fine storage detail             -> Snowflake storage metrics/history
```

Baseline diagnostic SQL:

```text
snowflake/monitoring/queries/cost_attribution.sql
```

Query-attributed compute excludes idle time; do not label it the full warehouse bill.

See ADR-026.

## 17. Verified CI status

### Platform Terraform

```text
Run:    33223588208
Commit: 509f2986dd9b74f063e7f65b4dfcf8d7655cf5ed
Result: SUCCESS
```

Passed organization, identity/dev|uat|prod, dev, project-identity/dev, uat, prod, fmt, Azure backend and S3 backend validation.

### Framework

Latest verified framework run after dbt resolver/package/actions documentation:

```text
Run:    33234750090
Commit: ceadb8c301aa068c78e5ca00c47b97195c59a2ab
Result: SUCCESS
```

The dbt target implementation was explicitly proven in run `33234538065`: pinned dbt install, `dbt deps`, offline `dbt parse`, and manifest assertion all succeeded.

### Health

```text
Metadata CI:   33234613472  SUCCESS
dbt Static CI: 33234696407  SUCCESS
```

### Transport

```text
Metadata CI:   33234663148  SUCCESS
dbt Static CI: 33234700682  SUCCESS
```

Static CI proves source/config/schema/package/macro validity. It does not prove live Snowflake authorization or runtime SQL behavior.

## 18. What has NOT happened yet

Do not claim these are complete:

- no real Azure Blob/S3 state control plane provisioned;
- no Snowflake DEV/UAT/PROD account bootstrap/import executed by this Terraform;
- no Terraform identity root applied to live Snowflake;
- no real DEV remote Terraform plan/apply;
- no `project-identity/dev` live apply;
- GitHub Environment `ci` values are not configured/tested against live Snowflake;
- no real PR workspace create/drop executed in Snowflake;
- no live dbt execution against Snowflake;
- live effective grants remain unverified;
- no UAT/PROD project deployment/promotion identities;
- no persisted cost views/resource monitors/budgets;
- no generic load strategy has yet been executed against Snowflake;
- no Health/Transport business model implementation yet;
- Kafka Connector, Snowpipe Streaming and Openflow remain deferred.

## 19. Next useful source work without live accounts

The environment resolver and reusable metadata/static dbt CI are now complete. Next source work should be:

```text
1. implement/test basic generic load primitives
   - full_refresh
   - append_only
   - incremental_merge
2. add query-tag integration at dbt invocation/hook boundary
3. implement reconciliation/freshness/audit primitives
4. define thin DEV deployment + UAT/PROD promotion identity/workflow contracts
5. only after those foundations, implement SCD2 variants and real project models
```

When real infrastructure becomes available:

```text
choose Azure Blob OR S3
-> provision state/OIDC
-> organization bootstrap/import
-> identity/dev apply
-> platform/dev plan/apply/verify
-> project-identity/dev apply
-> configure project GitHub Environment ci
-> real PR workspace create/drop test
-> live dbt smoke test
-> UAT
-> protected PROD
```

## 20. Important ADRs

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
```
