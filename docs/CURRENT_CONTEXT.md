# Enterprise Snowflake Platform — Current Context

> **Purpose:** Fast handoff for a new conversation/session. Read this file first, then `PROJECT_BLUEPRINT.md` for long-term architecture.
>
> **Updated:** 2026-08-29
>
> **Current phase:** Phase 1 platform + reusable framework foundation is source/static-CI proven. Documentation has been cross-repo audited against current source. No real Snowflake account bootstrap, Terraform apply, project deployment or live data execution has happened yet.

## 1. Non-negotiable rules

- Common technical behaviour is metadata-driven; genuine domain/business logic stays explicit SQL/code.
- Do not build a YAML programming language or over-abstract genuinely different project/source logic.
- No DEV/UAT/PROD Git branches. Promote immutable full project Git SHAs from reviewed `main` history.
- One Snowflake object has one authoritative lifecycle owner.
- Git is desired-state/configuration source of truth; `PLATFORM_CONTROL` is mutable runtime/operational state.
- Terraform defines stable platform resources/permission models; enterprise IdP/SCIM controls employee membership.
- Human and machine identities are separate.
- Ingestion technology stops at the project-owned stable RAW contract.
- Canonical layer vocabulary is `RAW -> STAGING -> INTERMEDIATE/CANONICAL -> MARTS -> SEMANTIC`; framework docs do not introduce separate Bronze/Silver physical layers.
- Shared account-local operational state must enforce domain isolation; caller convention is not an authorization boundary.
- Prefer Snowflake-native primitives before custom runtime state/orchestration.
- Dynamic Tables are optional execution/projection choices; classic regular-table paths remain available.
- Do not start Kafka Connector, direct Snowpipe Streaming or Openflow demos before live DEV foundation proof.

## 2. Repositories

```text
enterprise-snowflake-platform-infra
enterprise-snowflake-data-project-framework
enterprise-snowflake-demo-source-systems
enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
```

Ownership:

- **platform-infra** — account/platform Terraform, RBAC, warehouses, state/WIF, project workload identity boundaries, cost/governance and `PLATFORM_CONTROL` lifecycle.
- **data-project-framework** — bounded metadata validation, dbt macros/tests, query tags, workspace/target utilities, capture/checkpoint/quality/SCD primitives and reusable workflows.
- **demo-source-systems** — deterministic external-style source simulation/producers only.
- **health/transport** — project RAW contracts/config/business SQL/tests/semantic and later ingestion-specific configuration.

No placeholder directories or `.gitkeep`.

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

Published schemas initially: `MARTS`, `SEMANTIC`. RAW source-purpose schemas appear only when a real source is onboarded.

## 4. Human RBAC and compute

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
  -> READ
  -> WRITE
  -> OWNER
```

Policy:

- GUEST = published MARTS/SEMANTIC read-only + query compute.
- READER = all stable-layer read.
- DEV DEVELOPER = WRITE + personal schema creation + transform compute.
- UAT/PROD DEVELOPER = read-only by default.
- UAT/PROD human roles receive no permanent transform warehouse grant in the baseline.
- Emergency human UAT/PROD transform execution is JIT/break-glass through enterprise identity governance.
- Domain authority never implies another domain.

Employee membership flows through IdP/SCIM; ordinary joiner/leaver changes do not edit Terraform.

Warehouses:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
WH_PLATFORM_OPS
```

## 5. PR CI and stable deployment identities

DEV PR CI:

```text
SU_GITHUB_<DOMAIN>_CI
  -> AR_<DOMAIN>_CI
      -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> WH_<DOMAIN>_CI
      -> EXECUTE TASK
```

Stable DEV/UAT/PROD delivery:

```text
SU_GITHUB_<DOMAIN>_DEPLOY
  -> AR_<DOMAIN>_DEPLOY
      -> DR_<DOMAIN>_ANALYTICS_WRITE
      -> WH_<DOMAIN>_TRANSFORM
      -> CREATE STREAM
      -> CREATE TASK
      -> CREATE DYNAMIC TABLE
      -> EXECUTE TASK
```

No baseline `EXECUTE MANAGED TASK`; named warehouses are used.

All project workload identities use GitHub OIDC + Snowflake Workload Identity Federation with repository + GitHub Environment scoped subjects and account-scoped audiences. Health cannot authenticate as Transport and vice versa.

## 6. Immutable project delivery

Framework reusable workflow:

```text
enterprise-snowflake-data-project-framework/.github/workflows/project-deploy.yml
```

Health/Transport contain thin manual callers. Standard delivery requires full lowercase 40-character project/framework SHAs and:

1. enters the protected caller-repository target Environment;
2. reads environment-level Snowflake account/audience only after that environment is active;
3. checks out full current project `main` history;
4. proves requested project SHA is an ancestor of current `main`;
5. detached-checks out the exact project SHA;
6. checks out/verifies the exact framework SHA;
7. verifies project `dbt/packages.yml` uses the same framework SHA;
8. requests an account-scoped OIDC token;
9. authenticates as `SU_GITHUB_<DOMAIN>_DEPLOY -> AR_<DOMAIN>_DEPLOY`;
10. deploys to `<ENV>_<DOMAIN>` using `WH_<DOMAIN>_TRANSFORM`;
11. serializes deployments per domain/environment without cancelling an in-flight deployment.

An unmerged side-branch commit cannot be sent through the standard deployment path merely because its SHA exists.

Promotion is:

```text
same reviewed main-history project SHA
DEV -> UAT -> PROD
```

## 7. Current framework release and verification

Current **code release pinned by Health and Transport**:

```text
b1896aa110632e94c21010695ee000c9181d9caf
```

It is pinned consistently by project package metadata, metadata CI, dbt static CI, PR workspace caller and stable deployment caller.

Verified runs:

```text
Framework CI        33247852738  SUCCESS
Health Metadata     33247921191  SUCCESS
Health dbt Static   33247929378  SUCCESS
Transport Metadata  33247963393  SUCCESS
Transport dbt       33247973079  SUCCESS
```

Framework CI includes explicit workflow security assertions for protected-environment variable loading, full-SHA verification, main-history ancestry validation and exact detached checkout.

Documentation-only commits may exist on framework `main` after this release; do not confuse repository HEAD with the project-pinned executable framework revision. Do not repin project code merely because framework documentation changed.

## 8. Terraform lifecycle/state

Platform Terraform identities:

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Initial routine privileges:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Ten independent lifecycle states:

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

Per environment:

```text
identity/<env>
  -> platform/<env>
      -> project-identity/<env>
```

Backend profiles:

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

One deployment selects one authoritative writable backend. OneDrive/SharePoint is documentation/evidence storage, not live Terraform state.

Versions:

```text
Terraform CLI                 1.16.0
Snowflake Terraform provider  2.19.0
```

Latest RBAC/identity Terraform regression:

```text
run 33247440078 -> all 13 jobs SUCCESS
```

This validates fmt, all ten Terraform roots and both backend profiles. It does not prove live authorization.

## 9. RAW capture, runtime state and the open control-access boundary

Capture archetypes:

```text
snapshot
watermark
net_change
full_change
snapshot_diff
cursor_or_file
```

Capture fidelity:

```text
current_state
net_change
full_change
full_event
```

Source fidelity sets the maximum downstream history guarantee. Full snapshots needed for history/delete inference remain retained as immutable snapshot batches. Full-change/full-event sources preserve immutable event evidence in regular RAW tables before Stream consumers. A Stream is an offset/delta consumer, not the complete source audit history.

Framework documentation uses RAW as the authoritative evidence-layer term. Bronze/Silver are not additional platform schemas.

Mutable source progress and operational ledgers are structurally implemented under:

```text
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT
PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN
PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECK_RESULT
PLATFORM_CONTROL.OPERATIONS.ADVANCE_PIPELINE_CHECKPOINT(...)
```

Framework SQL primitives can read/write these contracts. However, **end-to-end project runtime authorization is not complete**: current domain deployment roles do not yet have a domain-scoped access surface to shared `PLATFORM_CONTROL.OPERATIONS` state.

Do not fix this with broad cross-domain table DML. Health must be unable to read/write Transport operational rows and vice versa. The current owner-rights checkpoint procedure accepts `project_code` from the caller, so unrestricted procedure usage without an additional domain guard would also be unsafe.

This open design/implementation requirement is documented in:

```text
docs/architecture/OPERATIONAL_CONTROL_ACCESS.md
```

Do not duplicate Snowflake-owned Stream offsets or Task run history into parallel framework state.

## 10. SCD architecture

Supported load strategies:

```text
full_refresh
append_only
incremental_merge
scd2_snapshot
scd2_merge
scd2_stream_task
```

`esf_configure_dataset()` remains intentionally limited to the three basic dbt materialization strategies. Checkpoint, quality and SCD behavior are separate dedicated framework primitives rather than hidden materialization hooks.

SCD2 canonical implementations use regular-table/Snowflake-native DML/Stream/Task patterns, not a Dynamic Table SCD2 wrapper.

Key reusable primitives:

```text
esf_scd1_merge_sql()
esf_scd1_dynamic_table_sql()
esf_scd2_snapshot_apply_sql()
esf_scd2_event_history_select()
esf_scd2_rebuild_affected_keys_sql()
esf_scd2_stream_task_sql()
esf_scd2_target_table_sql()
```

SCD2 invariants cover one-current-row, valid ranges, no overlap and deterministic unique version ordinal.

A deterministic SQL behavioral oracle covers duplicate replay, no-op state, update, delete/reinsert gap, late events and ordering ties. Static Framework CI proves parse/render/discovery; real Snowflake execution remains pending.

Architecture decisions:

- ADR-030 — basic materialization bridge; dedicated runtime/SCD primitives are outside that macro.
- ADR-031 — reusable capture archetypes + Dynamic Table fallback.
- ADR-035 — capture fidelity + reusable SCD consumer semantics.

The duplicate ADR-031 numbering that previously existed has been corrected. ADR-030/031 now also record current implementation status so their original phase language is not mistaken for present-day gaps.

## 11. Current domain contracts

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

The old Health `scd2_snapshot` documentation was wrong and has been corrected.

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

Direct Snowpipe Streaming and Kafka Connector must later converge on this same logical RAW contract.

## 12. Documentation audit completed 2026-08-29

The cross-repository audit corrected material drift in:

```text
platform README
PROJECT_BLUEPRINT.md
ACCOUNT_TOPOLOGY.md
RBAC_MODEL.md
REPOSITORY_LAYOUT.md
TERRAFORM_STATE_AND_IDENTITY.md
TERRAFORM_STANDARDS.md
NAMING_CONVENTIONS.md
terraform/README.md
terraform bootstrap runbook
framework README
framework workspace/query-tag pattern
framework capture-archetypes pattern
framework source-capture matrix
Health README
Transport README
demo-source README
ADR-030 implementation status
ADR-031 implementation status
ADR numbering
```

Major corrected drift included:

```text
8 lifecycle states -> 10
S3-only wording -> Azure-first/S3 selectable backend
DEV-CI-only identity model -> CI + DEV/UAT/PROD deployment identities
UAT/PROD ADMIN transform -> machine-only routine DEPLOY compute
Health scd2_snapshot -> actual scd2_merge/full-change CDC
SCD/quality/deployment marked future -> current implemented static-CI baseline
ambiguous duplicate ADR-031 -> ADR-031 capture + ADR-035 SCD consumers
Bronze/Silver aliases -> canonical RAW/downstream layer vocabulary
historical ADR phase wording -> explicit current implementation status
```

`PLATFORM_CONTROL` native-SQL deployment documentation and ADR-032 were reviewed and found consistent with current ownership/deployment boundaries; no change was required.

The audit also surfaced the domain-scoped operational control access gap described above. That is an implementation/design blocker, not merely stale documentation.

Framework pattern/product assertions were checked against current Snowflake documentation: ADAPTIVE Dynamic Table refresh is GA as of 2026-07-30; Data Quality Monitoring remains Enterprise Edition; Stream repeatable-read/offset-on-commit semantics match the framework pattern; Snowflake's current decision guidance keeps SCD2 history on Streams + Tasks rather than Dynamic Tables.

## 13. What is still genuinely incomplete

Do **not** claim production/live completion for any of the following:

```text
domain-scoped PLATFORM_CONTROL operational read/write API + RBAC bridge
real Azure Blob/S3 Terraform state control plane
real DEV/UAT/PROD Snowflake account bootstrap/import
identity/dev live apply
platform/dev real plan/apply
effective Snowflake grant verification
project-identity/dev live apply
Health/Transport GitHub Environments ci/dev live configuration proof
real PR workspace WIF create/drop
real stable DEV project deployment
live SCD2 behavioral oracle execution
UAT/PROD promotion
rollback/recovery/backfill automation
full observability dashboards
advanced governance policy rollout
Kafka/direct Snowpipe Streaming/Openflow implementation
```

## 14. Next execution gate

Work that can be completed before a real cloud/Snowflake environment:

```text
1. choose and implement domain-scoped PLATFORM_CONTROL operational access
2. add static security/contract tests proving no cross-domain control-state path
```

Then live control-plane proof:

```text
3. provision/select authoritative remote state backend
4. bootstrap/import Snowflake accounts
5. bootstrap identity/dev
6. reviewed platform/dev plan/apply
7. verify DEV RBAC/warehouses/PLATFORM_CONTROL
8. bootstrap project-identity/dev
9. configure Health/Transport GitHub Environments ci + dev
10. prove real PR workspace WIF create/drop
11. prove immutable reviewed-main SHA DEV deployment
12. prove unmerged side-branch SHA rejection
13. prove HEALTH cannot access TRANSPORT operational state and vice versa
14. execute deterministic SCD2 test in real Snowflake
15. repeat controlled lifecycle for UAT
16. repeat protected lifecycle for PROD
17. only then start streaming-ingestion comparison
```

Primary references:

- `docs/PROJECT_BLUEPRINT.md`
- `docs/architecture/ACCOUNT_TOPOLOGY.md`
- `docs/architecture/RBAC_MODEL.md`
- `docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`
- `docs/architecture/OPERATIONAL_CONTROL_ACCESS.md`
- `docs/architecture/REPOSITORY_LAYOUT.md`
- `docs/standards/TERRAFORM_STANDARDS.md`
- `docs/runbooks/terraform-platform-bootstrap.md`
- ADR-030, ADR-031, ADR-034, ADR-035
