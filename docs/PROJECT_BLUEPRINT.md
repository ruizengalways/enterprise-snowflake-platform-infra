# Enterprise Snowflake Platform — Project Blueprint

> **Status:** Phase 1 in progress — platform/domain/workspace/project-CI/metadata/dbt/basic-load foundations implemented in source/static CI; live remote state + Snowflake apply/verification remain.
>
> **Authority:** Canonical long-term architecture for the Enterprise Snowflake Platform.
>
> **Fast handoff:** Read [`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) first in a new conversation/session.

## 1. Goal

Build a production-grade reusable Snowflake platform/reference implementation suitable for real enterprise adoption and Senior/Principal Data Engineering / Snowflake Platform Engineering work.

The platform should let a new governed domain onboard quickly without copying platform mechanics, while keeping genuine business differences explicit and reviewable.

## 2. Core principles

1. **Metadata drives stable technical behaviour.** Business joins, calculations, domain rules and genuinely different source semantics remain explicit code.
2. **Do not build a YAML programming language.** Metadata is a bounded contract, not an orchestration DSL.
3. **Git is desired-state/configuration source of truth.** `PLATFORM_CONTROL` stores runtime/operational state.
4. **One object has one lifecycle owner.** Terraform, dbt, native SQL and runtime workflows must not fight over the same object.
5. **Promote immutable Git SHA.** Do not use DEV/UAT/PROD branches.
6. **Ingestion technology stops at the RAW contract.** Replacing Kafka/Openflow/Snowpipe Streaming must not force downstream redesign.
7. **Human and machine identities are separate.** Employees do not need Terraform knowledge to join a domain role.
8. **Least privilege before convenience.** Privilege expansion follows demonstrated requirements.
9. **Recovery, reconciliation, freshness, observability and cost attribution are design inputs, not later dashboards.**
10. **Do not over-engineer ahead of a real consumer.** No empty placeholder directories or speculative runtime tables.

## 3. Repository model

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

### Platform Infra

Owns Snowflake account/platform infrastructure, RBAC, warehouses, Terraform/WIF/state contract, workspace access boundaries, cost/governance/control-plane foundations.

### Data Project Framework

Owns reusable technical mechanics: metadata contracts/validation, dbt package/macros/tests, environment resolution, workspace/query-tag helpers, standard load strategies, reconciliation/freshness/audit mechanics and reusable delivery/recovery workflows.

### Domain Projects

Health/Transport own their RAW contracts, dataset configuration, sources, business SQL/tests, marts, semantic definitions and ingestion-specific configuration.

### Demo Source Systems

Represents deterministic systems outside Snowflake and stops at the source/RAW boundary.

## 4. Snowflake account topology

Canonical organization topology:

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

CI is not a fourth Snowflake account. PR CI runs in DEV but uses separate domain CI databases and compute.

UAT is a real account because it must validate account-scoped identities, integrations, parameters, RBAC/security boundaries and operational configuration before PROD.

## 5. Database and schema boundary

Database pattern:

```text
<ENVIRONMENT>_<DOMAIN>
```

Database means **environment × governed data product/domain**, not physical source system.

Do not create one database for every MSSQL/MySQL/API/file source merely for cost allocation.

Stable schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

`CANONICAL` is used when a distinct canonical layer is justified; it is not mandatory business complexity.

Published consumer schemas initially:

```text
MARTS
SEMANTIC
```

RAW source-purpose schemas are created only when a real source is onboarded, for example:

```text
RAW_EHR_MSSQL
RAW_BOOKING_MYSQL
RAW_INSURANCE_API
```

## 6. RAW contract boundary

Each project owns a stable RAW contract independent of ingestion implementation.

```text
External source
   -> ingestion mechanism
      -> project-owned RAW contract
         -> staging
            -> intermediate/canonical
               -> marts
                  -> Semantic Views
```

The RAW contract captures source/entity/grain/key, columns/types/nullability/classification, source timestamps, snapshot/append/CDC semantics, cadence, retention and breaking-change policy.

Changing ingestion technology must not require downstream model rewrites if the logical RAW contract is preserved.

## 7. Human RBAC

Every domain has independent account roles:

```text
AR_<DOMAIN>_GUEST
        ↓
AR_<DOMAIN>_READER
        ↓
AR_<DOMAIN>_DEVELOPER
        ↓
AR_<DOMAIN>_ADMIN
```

Every stable domain database has only its owning domain's database roles:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
        ↓
DR_<DOMAIN>_ANALYTICS_READ
        ↓
DR_<DOMAIN>_ANALYTICS_WRITE
        ↓
DR_<DOMAIN>_ANALYTICS_OWNER
```

### GUEST

Authenticated read-only consumer access to published schemas only:

```text
MARTS
SEMANTIC
```

GUEST is not Snowflake `PUBLIC` and not anonymous access.

### READER

Reads all stable domain layers.

### DEVELOPER

DEV receives WRITE and transform compute. UAT/PROD DEVELOPER remains read-only by default.

### ADMIN

Highest governed domain access tier. `OWNER` is an access-tier name; Terraform-managed database/schema ownership is not silently transferred away from Terraform.

Health authority never implies Transport authority.

## 8. Employee identity model

Terraform manages **what roles and grants exist**, not who works at the company.

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

Adding Alice to an existing Finance domain must not require Alice, her manager or normal IAM operators to modify Terraform.

## 9. Domain compute

Per domain:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV account only
```

Platform operations:

```text
WH_PLATFORM_OPS
```

Intent:

- GUEST/READER query on QUERY compute;
- DEV DEVELOPER adds TRANSFORM;
- CI compute is machine-only;
- UAT/PROD deployment compute will move to dedicated promotion identities rather than normal developers;
- warehouse is a primary compute/cost attribution boundary.

Environment metadata declares domain warehouse keys, so adding a new domain does not require copied root-Terraform grant blocks.

## 10. DEV personal workspaces

Human roles attach only to `DEV_<DOMAIN>` databases.

Personal schema convention:

```text
<DEVELOPER>_<LAYER>
```

Example:

```text
DEV_HEALTH.ALICE_SMITH_STAGING
```

DEV WRITE receives `CREATE SCHEMA` on the owning DEV database.

This prefix is a namespace convention, not strong per-person security isolation. Stronger isolation would require separately governed personal roles.

## 11. PR CI workspaces

Human domain roles do not attach to `CI_<DOMAIN>`.

Machine capability:

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> database USAGE + CREATE SCHEMA
  -> WH_<DOMAIN>_CI USAGE
```

Schema convention:

```text
PR_<NUMBER>_<LAYER>
```

Framework PR schemas are transient with zero-day Time Travel and explicit guarded cleanup.

## 12. Terraform ownership and lifecycle roots

Terraform selectively owns stable platform infrastructure. It does not own dbt models, employee membership or runtime data changes.

Current state/lifecycle boundaries:

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

Terraform baseline:

```text
Terraform CLI                 1.16.0
Snowflake Terraform provider  2.19.0
```

Every root commits `.terraform.lock.hcl` and static CI uses read-only lock mode.

## 13. Organization and platform Terraform identity

`organization/` alone uses ORGADMIN for controlled Snowflake account create/import.

Per account platform Terraform identity:

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Routine role baseline:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine Terraform never activates ACCOUNTADMIN, SYSADMIN or SECURITYADMIN.

Identity bootstrap may use ACCOUNTADMIN only to establish the machine user/role/WIF trust and is kept in separate state so routine automation cannot destroy its own authentication path.

## 14. Project CI identity

After `platform/dev` creates `AR_<DOMAIN>_CI`, the separate `project-identity/dev` lifecycle creates only service users and role assignment:

```text
SU_GITHUB_HEALTH_CI    -> AR_HEALTH_CI
SU_GITHUB_TRANSPORT_CI -> AR_TRANSPORT_CI
```

GitHub OIDC subject is repository + GitHub Environment `ci`.

Project CI service identities receive no account-level privileges.

## 15. OIDC / WIF

New CI automation avoids Snowflake passwords/private keys where possible.

Platform Terraform subjects are pinned to repository + environment (`dev`, `uat`, `prod`). Project CI subjects are pinned to their own domain repo + `ci` Environment.

Use account-scoped Snowflake OIDC audiences rather than the shared `snowflakecomputing.com` audience for these identities.

## 16. Terraform remote state

The platform is not AWS-dependent.

Supported execution adapters:

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

Committed Snowflake roots remain backend-agnostic. Execution materializes one backend declaration with:

```text
terraform/scripts/select-backend.sh
```

OneDrive/SharePoint may hold architecture/runbook/audit artifacts but is not the authoritative collaborative `terraform.tfstate` backend.

A deployment chooses one writable source of truth for each state.

## 17. Project metadata contracts

Framework schema version 1 covers:

```text
project metadata
  -> code / name / repository / owner team

dataset metadata
  -> RAW contract
  -> load strategy
  -> standard/custom implementation
  -> business key / watermark
  -> freshness / reconciliation

RAW contract
  -> source/entity/grain/key
  -> columns/types/nullability/classification
  -> source timestamp
  -> snapshot/append/CDC semantics
  -> cadence/retention/breaking-change policy
```

Cross-file validation is deliberately technical and bounded.

Business joins, formulas, free-form SQL and arbitrary workflow branching do not belong in metadata.

## 18. Current first domain contracts

Health `patient`:

```text
source_system: ehr_mssql
load_strategy: scd2_snapshot
business_key: patient_id
watermark: source_updated_at
change semantics: CDC + tombstone
freshness: 60/120 minutes
```

Transport `vehicle_position`:

```text
source_system: gtfs_realtime
load_strategy: append_only
watermark: event_timestamp
change semantics: append
freshness: 5/15 minutes
```

These contracts exist before ingestion-specific implementation so later ingestion choices converge on a stable downstream boundary.

## 19. dbt physical target resolution

Canonical stable reference:

```text
dbt-core      1.12.3
dbt-snowflake 1.12.0
```

The framework Python resolver is authoritative for environment routing.

Inputs:

```text
project_code
environment = dev | ci | uat | prod
workload    = query | transform | ci
optional developer identity
optional PR number
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
DEV personal -> DEV_<DOMAIN> / WH_<DOMAIN>_TRANSFORM / <DEVELOPER>_<LAYER>
PR CI        -> CI_<DOMAIN>  / WH_<DOMAIN>_CI        / PR_<NUMBER>_<LAYER>
UAT          -> UAT_<DOMAIN> / stable <LAYER>
PROD         -> PROD_<DOMAIN>/ stable <LAYER>
```

Framework dbt package owns common naming macros. Each root project keeps explicit thin wrapper macros so root-level override behavior is obvious.

Project model SQL uses `ref()` / `source()` and must not hard-code physical environment database names.

## 20. Project dbt profiles and immutable framework pinning

Checked-in project `profiles.yml` files contain no password/private key.

Human DEV defaults to external-browser authentication. Machine targets use Snowflake workload identity with OIDC and a short-lived token provided near execution.

Health and Transport use one aligned framework revision for metadata action, dbt package/static action and PR workspace workflow rather than independently drifting revisions.

## 21. Metadata-to-dbt bridge

Framework `render_dbt_vars.py` first validates project metadata and then exposes only bounded technical fields under:

```text
esf_project
esf_datasets
```

Reusable project static CI supplies these vars to offline `dbt parse`.

This makes metadata changes and dbt configuration one validation boundary without generating business SQL.

## 22. Basic standard load strategies

Approved vocabulary:

```text
full_refresh
append_only
incremental_merge
scd2_snapshot
scd2_merge
scd2_stream_task
```

Basic framework macro currently implements:

```text
full_refresh
  -> dbt table

append_only
  -> dbt incremental + append

incremental_merge
  -> dbt incremental + merge
  -> unique_key from dataset.business_key metadata
```

A standard model identifies its governed dataset; its SELECT/business logic stays explicit SQL.

`append_only` does not automatically invent a source checkpoint predicate. The rows returned on an incremental run are what dbt appends. Source-specific filtering remains explicit until a common checkpoint abstraction is proven safe.

`implementation: custom` fails the standard macro and is implemented explicitly by the project.

## 23. SCD2

Approved patterns remain:

```text
scd2_snapshot
scd2_merge
scd2_stream_task
```

Dynamic Tables are **not** an approved SCD2 mechanism.

Each SCD2 approach needs dedicated framework implementation/invariant tests for:

- current-row uniqueness;
- effective timestamps;
- late-arriving changes;
- deletes/tombstones;
- idempotent reruns;
- backfill/recovery behavior.

Until implemented, SCD2 strategies deliberately fail the basic-load macro instead of degrading to generic incremental merge.

## 24. PR CI workflow safety

Framework reusable PR workspace workflow:

```text
PR opened/reopened/synchronize -> create idempotent PR_<n>_* schemas
PR closed                      -> guarded drop of PR_<n>_* schemas
```

It requests an account-scoped GitHub OIDC token and runs only framework-generated workspace SQL while holding Snowflake credentials.

It does **not** currently execute arbitrary untrusted PR business code with Snowflake credentials.

The later full PR dbt execution design must preserve the same trust-boundary discipline.

## 25. Query tags and cost attribution

Canonical JSON query-tag fields:

```text
required: project, environment, workload
optional: source, pipeline, dataset, run_id, git_sha, pr_number, operation
```

No personal/secret/regulated/business payload data belongs in query tags.

Cost boundaries:

```text
domain storage/recovery         -> <ENVIRONMENT>_<DOMAIN>
compute                         -> WH_<DOMAIN>_<WORKLOAD>
query execution attribution     -> QUERY_TAG + QUERY_ATTRIBUTION_HISTORY
warehouse idle compute          -> WAREHOUSE_METERING_HISTORY
serverless/ingestion            -> service-specific usage histories
fine storage                    -> Snowflake storage metrics/history
```

Do not present query-attributed credits as the full warehouse bill because they exclude idle warehouse compute.

## 26. Data quality / reconciliation / freshness

Framework target capabilities:

```text
metadata validation
schema/contract checks
generic dbt tests
reconciliation measures
freshness checks
load audit records
runtime quality results
```

Dataset metadata may declare standard measures such as row count, distinct business key and min/max source timestamp. Framework behavior should remain bounded; project-specific quality rules stay in project tests.

Persist operational results in `PLATFORM_CONTROL.QUALITY` / `OBSERVABILITY` only when the first live consumer exists.

## 27. Observability and SLOs

Observe at minimum:

```text
ingestion freshness
pipeline/model run outcome
reconciliation status
DQ failures
warehouse/query usage
serverless ingestion usage
deployment/promotion outcome
recovery operations
```

SLO thresholds should be dataset/workload metadata where they are genuinely technical and repeatable.

## 28. Deployment and promotion

Target source-code promotion flow:

```text
feature branch / PR
   -> static validation
   -> isolated PR workspace validation
   -> merge immutable SHA
   -> DEV deployment
   -> UAT promotion of same SHA
   -> protected PROD promotion of same SHA
```

No environment branches.

Platform Terraform and data-project dbt deployment identities are separate workloads.

UAT/PROD promotion identities/workflows remain to be implemented.

## 29. Rollback and recovery

Derived PROD data recovery pattern:

```text
pre-release zero-copy clone
   -> deployment
   -> verification
   -> controlled SWAP/restore if rollback required
```

Do not blindly roll back RAW ingestion state as if it were replaceable derived data.

Recovery must distinguish:

- code rollback;
- derived-object/data rollback;
- replay/backfill;
- source correction;
- infrastructure recovery.

## 30. Semantic layer

Use native Snowflake Semantic Views as the governed semantic layer in the reference platform.

No Cube dependency is planned.

Semantic definitions are domain-owned but promoted/tested through the same project delivery lifecycle.

## 31. Ingestion roadmap

Do not start ingestion demonstrations before the platform/framework foundation is credible.

Transport later compares:

```text
producer -> direct Snowpipe Streaming -> RAW contract
```

and:

```text
producer -> Kafka -> Snowflake Kafka Connector -> RAW contract
```

Normally one comparison path is active at a time.

Health later demonstrates Openflow where appropriate.

Spark Streaming is not introduced without a requirement that Snowflake-native/Kafka paths cannot reasonably satisfy.

Marketplace Secure Shares are not an ingestion/streaming substitute for these demonstrations.

## 32. New-domain onboarding target

A future Finance onboarding should require small declarative platform metadata, not copied Terraform.

Expected standard resources:

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
DR_FINANCE_CI_WORKSPACE

WH_FINANCE_QUERY
WH_FINANCE_TRANSFORM
WH_FINANCE_CI
```

Employee counts do not change Terraform. Membership remains IdP/SCIM-driven.

## 33. Current verified source/static-CI status

Implemented and statically proven:

```text
3-account Terraform architecture
organization + Terraform WIF bootstrap roots
Azure Blob / S3 state adapters
domain databases/RBAC/GUEST/warehouses
DEV personal + machine-only CI workspace permissions
project-identity/dev source
project/dataset/RAW metadata contracts
metadata validation reusable action
workspace + query-tag utilities
dbt target resolver + dbt package
Health/Transport thin dbt shells
Health/Transport metadata + offline dbt CI
metadata -> dbt vars bridge
basic full_refresh / append_only / incremental_merge dbt configuration
cost-attribution diagnostic SQL
```

Still live-unproven:

```text
remote state control plane
Snowflake account bootstrap/import
Terraform identity apply
DEV platform plan/apply
effective live privileges
project CI identity apply
real PR schema create/drop
live dbt execution/data correctness
checkpoint/watermark runtime behavior
reconciliation/freshness/audit runtime
SCD2 implementations
UAT/PROD data-project promotion identities
resource monitors/budgets/persisted cost views
```

## 34. Next implementation sequence

Without live cloud/Snowflake accounts:

```text
1. integrate canonical QUERY_TAG into dbt lifecycle
2. implement reconciliation/freshness/audit primitives
3. design a bounded checkpoint/watermark helper
4. implement SCD2 snapshot/merge/stream-task patterns + invariant tests
5. define DEV deployment + UAT/PROD promotion identity/workflow contracts
```

When real infrastructure is available:

```text
choose Azure Blob OR S3
-> provision state + cloud OIDC
-> organization bootstrap/import
-> identity/dev apply
-> platform/dev plan/apply
-> Snowflake-side RBAC/object verification
-> project-identity/dev apply
-> configure project GitHub Environment ci
-> real PR workspace test
-> live dbt/basic-load smoke
-> UAT
-> protected PROD
```

## 35. Architecture decisions

Current key ADRs:

```text
ADR-018  three-account DEV/UAT/PROD topology
ADR-019  environment × domain database boundary
ADR-020  domain GUEST + workload warehouses
ADR-021  isolated ORGADMIN organization bootstrap
ADR-022  historical S3-only state choice — superseded
ADR-023  GitHub OIDC platform Terraform identity
ADR-024  Azure Blob/S3 Terraform state adapters
ADR-025  DEV personal + PR CI workspace lifecycle
ADR-026  query-tag + cost-attribution contract
ADR-027  project PR-CI OIDC identity lifecycle
ADR-028  project/dataset/RAW metadata contracts
ADR-029  dbt physical target resolution
ADR-030  basic metadata-driven dbt load strategies
```
