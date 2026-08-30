# Enterprise Snowflake Platform — Current Context

> **Purpose:** fast human handoff for the active workstream. Keep this file short. Detailed architecture belongs in the linked documents; machine contracts belong in schema/config/SQL files.
>
> **Updated:** 2026-08-30
>
> **Current phase:** source/static-CI foundation is strong enough to define domain-safe runtime control, metadata-driven SCD2, and safe initial snapshot -> incremental/CDC handoff. No real Snowflake account bootstrap, Terraform apply, project deployment, or live source execution has been proven yet.

## 1. Non-negotiable rules

- Common technical behavior is metadata-driven; genuine domain/source/business logic stays explicit.
- Do not turn YAML into a programming language.
- Human explanation belongs in `docs/`; machine contracts belong in schemas/config/contracts/SQL/tests.
- No DEV/UAT/PROD Git branches. Promote immutable reviewed Git SHAs.
- Git owns desired configuration; `PLATFORM_CONTROL` owns mutable runtime state.
- Shared runtime state must enforce domain isolation server-side. Caller convention is not authorization.
- Ingestion technology stops at the project-owned RAW contract.
- Canonical layers remain `RAW -> STAGING -> INTERMEDIATE/CANONICAL -> MARTS -> SEMANTIC`.
- Prefer Snowflake-native primitives; keep classic table/Stream/Task/DML paths available.
- Do not start Kafka Connector, direct Snowpipe Streaming, or Openflow demos before live DEV foundation proof.

## 2. Repository responsibilities

```text
enterprise-snowflake-platform-infra
  stable accounts/RBAC/warehouses/WIF/Terraform
  PLATFORM_CONTROL lifecycle and authorization surfaces

enterprise-snowflake-data-project-framework
  bounded metadata validation
  reusable dbt/capture/SCD/quality/runtime helpers
  reusable CI/deployment workflows

enterprise-snowflake-health-analytics
enterprise-snowflake-transport-analytics
  domain RAW contracts/config
  thin calls into framework primitives
  real domain-specific SQL where needed

enterprise-snowflake-demo-source-systems
  deterministic external-style source simulation only
```

## 3. Snowflake topology

```text
DEV account
  DEV_HEALTH
  CI_HEALTH
  DEV_TRANSPORT
  CI_TRANSPORT
  PLATFORM_CONTROL

UAT account
  UAT_HEALTH
  UAT_TRANSPORT
  PLATFORM_CONTROL

PROD account
  PROD_HEALTH
  PROD_TRANSPORT
  PLATFORM_CONTROL
```

CI is a database boundary inside the DEV account, not a fourth Snowflake account.

Per-domain compute remains:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI       # DEV account only
WH_PLATFORM_OPS
```

## 4. Stable framework baseline versus active stacked work

Framework `main` currently includes merged domain-scoped operational API helpers:

```text
bbd5e9b2ee30ea911e513074ff5aa15936b994fb
```

Active framework stack:

```text
PR #2  feature/metadata-driven-scd2-contract
       head e0e6f44af1bf97354adf24535729c86a81b3e4d0
       metadata-driven snapshot/event SCD2
       Framework CI green

PR #3  feature/bootstrap-handoff-contract
       base: PR #2 branch
       head f16ca40c8bed0c81b9e43bc86c8f3a0941249c46
       initial snapshot -> incremental/CDC handoff
       Framework CI green
       Bootstrap Contract CI green
```

Stacking is deliberate: reviewers should see the bootstrap delta independently from the SCD2 delta. Retarget PR #3 to `main` after PR #2 merges.

## 5. Platform control work

Platform-infra PR #1:

```text
feature/domain-scoped-operational-control
verified implementation/doc head 19e62dae017a506b3f51eddd210976a31c4b8a4b
Platform Control SQL CI run 33290867268: SUCCESS
current branch may contain later CURRENT_CONTEXT-only commits after that verified head
```

It contains two separate generated authorization surfaces plus deployment/verification packaging.

Normal runtime control:

```text
<DOMAIN>_PIPELINE_CHECKPOINT
<DOMAIN>_PIPELINE_RUN
<DOMAIN>_PIPELINE_CHECK_RESULT

<DOMAIN>_ADVANCE_PIPELINE_CHECKPOINT
<DOMAIN>_PIPELINE_RUN_START
<DOMAIN>_PIPELINE_RUN_FINISH
<DOMAIN>_RECORD_PIPELINE_CHECK_RESULT
```

Initial bootstrap control:

```text
<DOMAIN>_PIPELINE_BOOTSTRAP

<DOMAIN>_PIPELINE_BOOTSTRAP_START
<DOMAIN>_PIPELINE_BOOTSTRAP_MARK_SNAPSHOT_LANDED
<DOMAIN>_PIPELINE_BOOTSTRAP_MARK_VALIDATED
<DOMAIN>_PIPELINE_BOOTSTRAP_COMMIT_HANDOFF
```

Deployment and verification packaging:

```text
render_domain_access.py
  normal domain surface only

render_domain_bootstrap_access.py
  bootstrap surface only

render_deployment_bundle.py
  packages ordered base SQL + both generated surfaces
  no authentication and no credentials

render_verification_sql.py
  derives expected views/procedures/grants from the same environment metadata
  rejects missing domain object grants and direct project grants on shared base tables
  no authentication and no credentials
```

The preferred future protected-workflow path is:

```text
authenticate
  -> render/execute one environment deployment bundle
  -> render/execute one environment verification SQL file
```

Workflow YAML should not duplicate the seven-step SQL dependency order or per-domain object/grant lists.

Project roles receive generated domain views/procedures only, not direct DML on shared base tables. Project and environment are fixed server-side.

Read:

```text
docs/architecture/OPERATIONAL_CONTROL_ACCESS.md
docs/architecture/BOOTSTRAP_HANDOFF_CONTROL.md
snowflake/control/operations/DEPLOYMENT.md
```

## 6. Bootstrap safety contract

Machine RAW metadata is intentionally small:

```yaml
capture:
  bootstrap:
    mode: snapshot_then_incremental
    snapshot_consistency: at_handoff_position
    incremental_start: exclusive | inclusive_with_deduplication
    reconciliation_required: true
```

Source-specific LSN/cursor/snapshot mechanics are not encoded in generic YAML.

Platform lifecycle:

```text
BOUNDARY_CAPTURED
  -> SNAPSHOT_LANDED
  -> SNAPSHOT_VALIDATED
  -> HANDOFF_COMMITTED
```

Current static invariants:

- `SNAPSHOT_VALIDATED` requires explicit `reconciliation_passed = TRUE` plus structured details.
- Initial bootstrap rejects an already-existing steady-state checkpoint.
- Final handoff rejects a different existing checkpoint, preventing checkpoint rewind.
- Final checkpoint write + `HANDOFF_COMMITTED` run in one explicit transaction.
- The rollback handler is scoped to the transaction block; precondition errors are outside it.
- Cross-domain project/environment values are not caller-controlled.

## 7. SCD2 contract

Standard SCD2 is strategy-specific rather than one oversized metadata shape.

```text
scd2_snapshot
  tracked attributes
  snapshot execution supplies effective time

scd2_merge / scd2_stream_task
  effective timestamp
  deterministic order columns
  tracked attributes
  tombstone semantics where present
  rebuild_affected_keys late-arrival policy
```

Standard event-history SCD2 requires append-preserved `full_change`/`full_event` capture. Ordering must preserve RAW ordering and include non-business-key idempotency columns.

A pure-Python behavior oracle covers replay, updates, late arrival, delete, and reinsert independently from SQL generation.

Read:

```text
enterprise-snowflake-data-project-framework/docs/patterns/metadata-driven-scd2.md
```

## 8. Domain reference integrations

Health PR #1:

```text
feature/domain-operational-contract
head 736460181569d24e5b341955cac94bd9f0cbf87d
dbt Static CI: green
PR Workspace: blocked by live Snowflake/WIF environment configuration
```

It proves the domain-safe operational API is not Transport-specific.

Transport PR #1:

```text
feature/domain-operational-contract
head 7cb4e52b6184e41d78a0a0867241404bf54179a1
Metadata CI: green
dbt Static CI: green
PR Workspace: blocked by live Snowflake/WIF environment configuration
```

It adds `vehicle_status` as the reference metadata-driven SCD2 dataset.

Transport PR #2 is stacked on PR #1:

```text
feature/bootstrap-handoff-contract
head 69158c5b80afd073298a29c267ce560ca9692590
framework pin f16ca40c8bed0c81b9e43bc86c8f3a0941249c46
Metadata CI: green
dbt Static CI: green
PR Workspace: blocked by live Snowflake/WIF environment configuration
```

It adds the `vehicle_status` bootstrap handoff reference contract and thin offline renderer.

## 9. What static CI proves versus what it does not

Static CI currently proves:

- metadata schema shape and semantic compatibility;
- dbt parse/render paths;
- deterministic SCD2 semantic fixture behavior;
- generated domain object names and grants;
- absence of project direct DML grants on shared operational tables;
- server-fixed project/environment authorization surfaces;
- bootstrap state-transition SQL shape;
- explicit reconciliation-pass gating;
- checkpoint-regression guards;
- atomic handoff transaction shape;
- deterministic deployment-bundle dependency ordering for DEV/UAT/PROD;
- generation of post-deploy checks for expected views/procedures, SELECT/USAGE grants, and forbidden shared-base grants.

Static CI does **not** prove:

- real Snowflake ownership/privilege behavior;
- WIF authentication;
- transaction and concurrency behavior under real sessions;
- Stream/Task runtime behavior;
- warehouse/query performance;
- a real source's consistent snapshot + position mechanism;
- recovery after real source/network failures.

## 10. Current live blocker

No real DEV Snowflake bootstrap has been completed.

The project PR Workspace workflows currently fail before Snowflake work because the GitHub `ci` Environment is missing the approved Snowflake WIF configuration, including:

```text
SNOWFLAKE_ACCOUNT
SNOWFLAKE_OIDC_AUDIENCE
```

The wider DEV bootstrap also still needs the real account, platform/project identities, and corresponding environment variables.

The protected platform operational SQL deployment workflow has **not** yet been wired to execute the generated environment deployment bundle and generated verification SQL. These renderers reduce that future workflow change to deterministic no-credential scripts; they do not themselves deploy anything.

Do not describe PR #1 objects as deployed until protected workflow wiring and live verification are complete.

## 11. Recommended merge/rebase order

```text
1. framework PR #2  metadata-driven SCD2
2. framework PR #3  bootstrap handoff; retarget to main
3. platform-infra PR #1 after review of both control surfaces
4. Transport PR #1 domain runtime + SCD2
5. Transport PR #2 bootstrap handoff; retarget to main after PR #1
6. Health PR #1 domain runtime proof
```

Exact order between platform and domain PRs can vary because current proof is static, but do not merge a domain project expecting a runtime surface that the target Snowflake environment has not deployed.

## 12. Next engineering gate

Before adding new ingestion technologies, complete live DEV proof in this order:

```text
Snowflake DEV + GitHub WIF bootstrap
  -> render one DEV PLATFORM_CONTROL deployment bundle
  -> execute bundle through protected workload identity
  -> execute generated post-deploy verification
  -> prove HEALTH/TRANSPORT cross-domain denial
  -> prove normal checkpoint/run/check runtime
  -> run bootstrap fail-closed state transitions
  -> prove reconciliation FALSE cannot validate
  -> prove checkpoint rewind is rejected
  -> atomically commit handoff checkpoint
  -> connect one real or deterministic external-style source
  -> prove initial snapshot -> incremental/CDC handoff
  -> prove retry/recovery/reconciliation
  -> prove SCD2 rebuild from retained event evidence
```

Only after that foundation should Kafka Connector, direct Snowpipe Streaming, or Openflow comparison work begin.

## 13. Authoritative human documents

Use this file only as an index. Follow the dedicated documents for detail:

```text
PROJECT_BLUEPRINT.md
docs/architecture/ACCOUNT_TOPOLOGY.md
docs/architecture/RBAC_MODEL.md
docs/architecture/OPERATIONAL_CONTROL_ACCESS.md
docs/architecture/BOOTSTRAP_HANDOFF_CONTROL.md
docs/architecture/PIPELINE_PATTERN_COVERAGE.md
docs/runbooks/terraform-platform-bootstrap.md
snowflake/control/operations/DEPLOYMENT.md
```

Framework-specific human guidance lives in that repository's `docs/patterns/`. Machine schemas/configuration remain authoritative for accepted metadata shape; prose must not override them.
