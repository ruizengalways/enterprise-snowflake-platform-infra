# Enterprise Snowflake Platform — Current Context

> **Purpose:** Fast handoff for a new conversation/session. Read this first, then `PROJECT_BLUEPRINT.md` for long-term architecture.
>
> **Updated:** 2026-08-29
>
> **Current phase:** Phase 1 platform + reusable framework foundation is source/static-CI proven. No real Snowflake account bootstrap, Terraform apply, project deployment, or live data execution has happened yet.

## 1. Non-negotiable design rules

- Common technical behaviour is metadata-driven; genuine domain/business logic stays explicit SQL/code.
- Do not create a YAML programming language or over-abstract differences that are genuinely project-specific.
- No DEV/UAT/PROD Git branches. Promote immutable full Git SHAs.
- One Snowflake object has one authoritative lifecycle owner.
- Git is configuration source of truth; `PLATFORM_CONTROL` is runtime/operational state.
- Terraform defines stable platform resources and permission models; enterprise IdP/SCIM controls who has human access.
- Human and machine identities are separate.
- Ingestion technology stops at the project-owned stable RAW contract.
- Prefer Snowflake-native primitives before custom runtime state/orchestration.
- Dynamic Tables are optional execution choices; classic regular-table equivalents remain available.
- Do not start Kafka Connector, direct Snowpipe Streaming or Openflow demos before the platform/framework foundation is live-proven.

## 2. Repositories

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

Ownership:

- **platform-infra** — account/platform Terraform, RBAC, warehouses, state/WIF, workspace/deployment access, cost/governance and `PLATFORM_CONTROL` lifecycle.
- **data-project-framework** — bounded metadata schemas/validation, dbt macros, query tags, workspace utilities, capture/checkpoint/quality/SCD primitives and reusable workflows.
- **demo-source-systems** — deterministic external-style source simulation only.
- **health/transport** — project contracts/config/business SQL/tests/semantic and ingestion configuration.

No placeholder directories or `.gitkeep`. Project repos stay thin and consume immutable framework revisions.

## 3. Snowflake topology

```text
Snowflake Organization
├── DEV account
│   ├── DEV_HEALTH
│   ├── CI_HEALTH
│   ├── DEV_TRANSPORT
│   ├── CI_TRANSPORT
│   └── PLATFORM_CONTROL
├── UAT account
│   ├── UAT_HEALTH
│   ├── UAT_TRANSPORT
│   └── PLATFORM_CONTROL
└── PROD account
    ├── PROD_HEALTH
    ├── PROD_TRANSPORT
    └── PLATFORM_CONTROL
```

CI is not a fourth account. Database boundary is environment × governed domain/data product, not physical source.

Stable transform schemas:

```text
STAGING
INTERMEDIATE
CANONICAL
MARTS
SEMANTIC
```

Published schemas initially: `MARTS`, `SEMANTIC`. RAW schemas appear only when a real source is onboarded, for example `RAW_EHR_MSSQL`.

## 4. Human identity and RBAC

Per-domain human hierarchy:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
  -> SYSADMIN
```

Stable database roles:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
  -> DR_<DOMAIN>_ANALYTICS_READ
  -> DR_<DOMAIN>_ANALYTICS_WRITE
  -> DR_<DOMAIN>_ANALYTICS_OWNER
```

Policy:

- GUEST = authenticated published-data read-only + query warehouse.
- READER = all stable-layer read.
- DEV DEVELOPER = WRITE + personal schema creation + transform compute.
- UAT/PROD DEVELOPER = read-only by default.
- UAT/PROD ADMIN does **not** receive permanent transform warehouse usage in the baseline.
- Human emergency UAT/PROD transform execution is JIT/break-glass through enterprise identity governance.
- Domain authority never implies another domain.

Employee lifecycle:

```text
Employee / contractor
  -> Entra ID / Okta group
  -> SCIM / approved provisioning
  -> AR_<DOMAIN>_<CAPABILITY>
```

Ordinary employees do not edit Terraform to join a role or use a warehouse. Terraform manages the permission model; the IdP manages who has permission.

## 5. Warehouses

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV account only
WH_PLATFORM_OPS
```

Baseline grants:

```text
GUEST                 -> QUERY
DEV DEVELOPER         -> TRANSFORM
AR_<DOMAIN>_CI        -> CI warehouse
AR_<DOMAIN>_DEPLOY    -> TRANSFORM
AR_PLATFORM_ENGINEER  -> PLATFORM_OPS
```

UAT/PROD routine transform compute is machine-only through deployment automation.

## 6. Personal DEV and PR CI workspaces

Human roles attach to `DEV_<DOMAIN>`, never `CI_<DOMAIN>`.

Personal namespace:

```text
<DEVELOPER>_<LAYER>
```

Machine-only CI capability:

```text
SU_GITHUB_<DOMAIN>_CI
  -> AR_<DOMAIN>_CI
      -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
          -> USAGE + CREATE SCHEMA on CI_<DOMAIN>
      -> USAGE on WH_<DOMAIN>_CI
      -> EXECUTE TASK
```

No serverless `EXECUTE MANAGED TASK` is granted.

PR schemas:

```text
PR_<NUMBER>_<LAYER>
```

Reusable framework PR workflow creates/drops guarded ephemeral schemas and does not execute untrusted project PR business code under Snowflake credentials.

## 7. Stable project deployment identity

Every domain/environment account has an independent deployment role:

```text
SU_GITHUB_<DOMAIN>_DEPLOY
  -> AR_<DOMAIN>_DEPLOY
      -> DR_<DOMAIN>_ANALYTICS_WRITE
      -> USAGE on WH_<DOMAIN>_TRANSFORM
      -> CREATE STREAM
      -> CREATE TASK
      -> CREATE DYNAMIC TABLE
      -> EXECUTE TASK
```

`AR_<DOMAIN>_DEPLOY` is outside the human role hierarchy and owns long-lived project runtime objects created by delivery.

Current derived service users include:

```text
SU_GITHUB_HEALTH_DEPLOY
SU_GITHUB_TRANSPORT_DEPLOY
```

in DEV/UAT/PROD, each bound to its same-domain deployment role in that Snowflake account.

GitHub OIDC subjects are analytics-repository + GitHub Environment scoped. Health cannot authenticate as Transport and vice versa. All Snowflake workload identities use an account-scoped OIDC audience rather than the shared `snowflakecomputing.com` audience.

See ADR-034.

## 8. Immutable project delivery

Framework reusable workflow:

```text
enterprise-snowflake-data-project-framework/.github/workflows/project-deploy.yml
```

Health/Transport contain thin manual `deploy.yml` callers. Deployment requires:

```text
full 40-character project Git SHA
full 40-character framework Git SHA
```

The reusable workflow:

1. accepts only `dev`, `uat` or `prod`;
2. checks out the exact project SHA;
3. checks out the exact framework SHA;
4. verifies project `dbt/packages.yml` uses that same framework revision;
5. targets the selected protected GitHub Environment;
6. requests an account-scoped GitHub OIDC token;
7. authenticates as `SU_GITHUB_<DOMAIN>_DEPLOY` / `AR_<DOMAIN>_DEPLOY`;
8. targets `<ENV>_<DOMAIN>` and `WH_<DOMAIN>_TRANSFORM`;
9. runs dbt deployment;
10. serializes deployments per domain/environment with `cancel-in-progress: false`.

Promotion means:

```text
same project Git SHA
DEV -> UAT -> PROD
```

The environment changes; the code revision does not.

No live deployment has executed yet because real Snowflake accounts/GitHub Environment variables have not been bootstrapped.

## 9. Framework immutable revision

Current framework release pinned by Health and Transport:

```text
f21fe2b00c20d56f45d7673ac79ff5aa1029338c
```

The same SHA is used by:

- project `dbt/packages.yml`;
- metadata validation action;
- dbt static action;
- PR workspace reusable workflow;
- project deployment reusable workflow.

Relevant validation:

- Framework run `33246689595` — SUCCESS.
- Health Metadata CI `33247181047` — SUCCESS.
- Health dbt Static CI `33247192592` — SUCCESS.
- Transport Metadata CI `33247223896` — SUCCESS.
- Transport dbt Static CI `33247231405` — SUCCESS.

## 10. Terraform identity and state lifecycle

Platform Terraform identities:

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Routine privileges initially:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine Terraform never activates ACCOUNTADMIN/SYSADMIN/SECURITYADMIN. Identity bootstrap roots may use ACCOUNTADMIN only to establish dedicated WIF service users/role assignments. Organization lifecycle alone may use ORGADMIN.

Ten independent Terraform state objects:

```text
organization
identity/dev
identity/uat
identity/prod
platform/dev
platform/uat
platform/prod
project-identity/dev
project-identity/uat
project-identity/prod
```

Project identity dependency:

```text
identity/<env>
  -> platform/<env>
      -> project-identity/<env>
```

The platform root creates target machine roles first; project-identity then creates WIF service users bound to those existing roles.

Remote-state profiles:

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

One deployment selects one writable backend. OneDrive/SharePoint is for docs/audit evidence, not live Terraform state.

Versions:

```text
Terraform CLI                 1.16.0
Snowflake Terraform provider  2.19.0
```

Latest RBAC/identity Terraform regression after removing UAT/PROD standing ADMIN transform compute:

```text
run 33247440078 -> all jobs SUCCESS
```

This includes fmt, DEV/UAT/PROD roots, identity/dev|uat|prod, project-identity/dev|uat|prod, and Azure/S3 backend profile validation.

## 11. RAW capture contract

Source onboarding maps real source patterns to bounded technical capture archetypes:

```text
snapshot
watermark
net_change
full_change
snapshot_diff
cursor_or_file
```

Capture fidelity is separate:

```text
current_state
net_change
full_change
full_event
```

Bounded metadata includes archetype, fidelity, checkpoint kind, deterministic ordering, idempotency identity and optional watermark lookback.

Important rules:

- Source fidelity sets the maximum downstream history guarantee.
- Full snapshots required for delete inference/history/replay are preserved as immutable snapshot batches; destructive overwrite cannot be the only evidence.
- Full-change/full-event capture first preserves immutable events in a regular Snowflake table.
- A Stream is a delta/offset consumer, not the complete CDC history store.
- Metadata validation rejects impossible capture/SCD combinations and nullable business keys.

## 12. Runtime state and observability

Mutable checkpoint/progress state lives in:

```text
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT
```

Operational ledgers:

```text
PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECK_RESULT
```

Native procedure:

```text
PLATFORM_CONTROL.OPERATIONS.ADVANCE_PIPELINE_CHECKPOINT(...)
```

Framework uses native Snowflake capabilities for Streams/Tasks/Dynamic Tables and Snowflake data-quality primitives where appropriate. Custom state is bounded to information Snowflake does not already own, such as source checkpoints, run correlation and reconciliation evidence.

## 13. SCD architecture

Supported load strategies:

```text
full_refresh
append_only
incremental_merge
scd2_snapshot
scd2_merge
scd2_stream_task
```

SCD2 history does not use Dynamic Tables as the canonical implementation.

Key primitives:

```text
esf_scd1_merge_sql()
esf_scd2_snapshot_apply_sql()
esf_scd2_event_history_select()
esf_scd2_rebuild_affected_keys_sql()
esf_scd2_stream_task_sql()
esf_scd2_target_table_sql()
```

SCD2 invariants cover one-current-row, valid ranges, no overlap and unique version ordinal.

A deterministic Snowflake SQL behavioral oracle is implemented as a dbt singular test. It covers duplicate replay, no-op same state, update, delete/reinsert gap, late-arriving events, ordering ties and equal-timestamp versions. Framework CI parses/renders/discovers this test offline; real Snowflake execution remains part of the live DEV verification gate.

For Stream-backed SCD2, Snowflake owns Stream offset/retry semantics. The framework does not invent a parallel custom offset runtime.

## 14. Current domain contracts

Health `patient`:

```text
source_system:       ehr_mssql
load_strategy:       scd2_merge
business_key:        patient_id
watermark:           source_updated_at
capture archetype:   full_change
fidelity:            full_change
checkpoint:          source_position
ordering:            source_sequence
idempotency:         patient_id + source_sequence
change semantics:    CDC + tombstone delete
freshness:           warn 60 min / error 120 min
```

Transport `vehicle_position`:

```text
source_system:       gtfs_realtime
load_strategy:       append_only
business identity:   vehicle_id
watermark:           event_timestamp
capture archetype:   full_change
fidelity:            full_event
checkpoint:          source_position
idempotency:         vehicle_id + event_timestamp
change semantics:    append
freshness:           warn 5 min / error 15 min
```

Transport ingestion technology remains deliberately deferred. Direct Snowpipe Streaming and Kafka Connector must later converge on the same logical RAW contract.

## 15. `PLATFORM_CONTROL` lifecycle

Ownership boundary:

```text
Terraform
  -> PLATFORM_CONTROL database
  -> managed schemas / stable access boundary

platform native SQL
  -> operational tables/procedures inside PLATFORM_CONTROL
```

Native SQL currently owns checkpoint/run/check-result tables and the checkpoint advancement procedure. Do not use Terraform `null_resource`/`local-exec` to own these operational SQL objects.

## 16. Next execution gate

Do not start broad ingestion/streaming implementation yet.

The next real milestone is live DEV control-plane proof:

```text
1. provision/select authoritative remote state backend
2. bootstrap/import DEV/UAT/PROD Snowflake accounts as applicable
3. bootstrap identity/dev
4. run reviewed platform/dev plan/apply
5. verify RBAC/warehouses/PLATFORM_CONTROL structure
6. bootstrap project-identity/dev
7. configure Health/Transport GitHub Environments ci + dev
8. prove PR workspace WIF create/drop
9. prove immutable DEV project deployment WIF
10. execute the deterministic SCD2 singular test in real Snowflake
11. only then progress UAT, PROD and later streaming demos
```

See:

- `docs/runbooks/terraform-platform-bootstrap.md`
- `docs/architecture/RBAC_MODEL.md`
- `docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`
- ADR-034
