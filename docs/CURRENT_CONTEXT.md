# Enterprise Snowflake Platform — Current Context

Concise human handoff for a new conversation. Detailed architecture belongs in linked docs; machine truth belongs in Terraform/config/schema/SQL/tests.

## Current phase

The source/static foundation now includes domain-scoped runtime/bootstrap control, Medallion database topology, Git-owned dataset configuration snapshots, metadata-driven SCD1/SCD2, thin domain deployment wrappers, and generation-aware full dataset reset.

No real Snowflake DEV bootstrap, WIF authentication, Terraform apply, PLATFORM_CONTROL deployment or live source handoff has been proven yet.

## Non-negotiable rules

- Common technical behavior is metadata-driven; genuine source/domain/business logic stays explicit.
- Do not turn YAML into a programming language.
- Human docs and machine contracts stay separate.
- Promote immutable reviewed Git SHAs; do not use DEV/UAT/PROD Git branches.
- Git owns desired dataset configuration.
- `PLATFORM_CONTROL.CONFIG` stores immutable deployment audit/readback state, not editable config.
- `PLATFORM_CONTROL.OPERATIONS` stores mutable runtime state.
- Domain isolation is enforced server-side through generated secure views / owner-rights procedures.
- Full reset is a recovery operation, not a substitute for repair/replay.
- Do not start Kafka Connector, direct Snowpipe Streaming or Openflow comparison before live DEV foundation proof.

## Account and domain topology

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

Stable domain databases use:

```text
BRONZE
SILVER_STAGING
SILVER_INTERMEDIATE
SILVER_CANONICAL
GOLD_MARTS
GOLD_SEMANTIC
DQ
```

Ordinary new sources share the domain `BRONZE` schema. A source-specific schema/database is a governance/security/lifecycle exception, not the default connector boundary.

## Platform control stack

Platform PR #1:

```text
feature/domain-scoped-operational-control
```

It provides domain-scoped `OPERATIONS` surfaces for checkpoint, run, quality-result and bootstrap state. Project roles receive generated domain views/procedures rather than direct shared-table DML. Bootstrap enforces explicit reconciliation success, checkpoint-regression denial and atomic handoff commit.

Platform PR #2 is stacked on PR #1:

```text
feature/medallion-dataset-control-plane
```

It adds Medallion schemas plus:

```text
PLATFORM_CONTROL.CONFIG.DATASET_CONFIG_SNAPSHOT
<DOMAIN>_DATASET_CONFIG_SNAPSHOT
<DOMAIN>_REGISTER_DATASET_CONFIG_SNAPSHOT
```

Git remains configuration truth; CONFIG is immutable deployment audit/readback state.

Platform PR #3 is stacked on PR #2:

```text
feature/dataset-reset-generation
verified head c20c09c0c5f51dff17ebc5fb3eec75c89c5ce5a2
Terraform CI #167: SUCCESS
Platform Control SQL CI #37: SUCCESS
```

It adds generation-aware runtime state and full reset control:

```text
PLATFORM_CONTROL.OPERATIONS.DATASET_LIFECYCLE
PLATFORM_CONTROL.OPERATIONS.DATASET_RESET

PIPELINE_CHECKPOINT     + GENERATION
PIPELINE_BOOTSTRAP      + GENERATION
PIPELINE_RUN            + GENERATION
PIPELINE_CHECK_RESULT   + GENERATION

<DOMAIN>_DATASET_LIFECYCLE
<DOMAIN>_DATASET_RESET
<DOMAIN>_DATASET_RESET_START
<DOMAIN>_DATASET_RESET_COMPLETE
```

Reset lifecycle:

```text
ACTIVE generation N
  -> RESETTING
  -> explicit domain cleanup
  -> generation N+1 / READY_FOR_INITIAL_LOAD
  -> normal main pipeline succeeds / checkpoint advances
  -> ACTIVE
```

Old generation runtime records remain auditable. Current checkpoint/bootstrap views resolve only the active generation, so a new generation cannot accidentally reuse the previous checkpoint.

Reset start rejects a current-generation `RUNNING` pipeline. Normal dataset runtime writes reject `RESETTING`. A cleanup failure leaves the dataset `RESETTING`; the same reset ID is retry-safe only while it remains `RESETTING`. Reusing a `READY_FOR_RELOAD` or `COMPLETED` reset ID fails closed before any cleanup can run.

## Recovery RBAC

Each domain receives:

```text
AR_<DOMAIN>_RECOVERY
```

This is intended for Senior Data Engineer+ operational recovery. It deliberately does not require a mandatory multi-person approval chain. Domain Admin inherits Recovery so incident recovery does not depend on one specific person being available.

Recovery receives the domain capabilities needed for a fast reset, including domain table `TRUNCATE` and the domain transform warehouse, plus domain-scoped reset views/procedures. It does not receive direct mutation privileges on shared PLATFORM_CONTROL base tables or cross-domain recovery rights.

This keeps full reset practical for incidents such as a materially incorrect dashboard or a small dataset where rebuilding from source is faster than targeted repair.

## Framework baseline

Current reset-aware immutable framework pin:

```text
8afe208bd911a59b9334add78a53878ffea93087
Framework CI #181: SUCCESS
```

Framework PR stack:

```text
PR #2 metadata-driven SCD2
  -> PR #3 bootstrap handoff
      -> PR #4 Medallion + config snapshot + stable deployment
          -> PR #5 bounded full-reset helpers
```

PR #5 adds domain reset relation/procedure helpers, a bounded explicit reset SQL renderer and an execution macro that performs start -> explicit truncate list -> complete. Domain repositories own the cleanup list; framework metadata does not accept arbitrary runtime relation names.

## Domain consumers

Transport reset PR #4:

```text
feature/dataset-reset-generation
verified source/static head 649021fa5f84e580361e86d9bf8c66664e581a04
dbt Static CI #53: SUCCESS
PR Workspace #34: blocked at Load approved Snowflake environment configuration
```

`vehicle_status` has an explicit reset plan spanning its reconstructable Bronze, Silver and Gold Mart tables. `vehicle_position` remains an append/event dataset and is not automatically added to that reset.

Health reset PR #3:

```text
feature/dataset-reset-generation
verified source/static head d33f92a928e3c9ca553a843c2c52c4952d86a13b
dbt Static CI #34: SUCCESS
PR Workspace #15: blocked at Load approved Snowflake environment configuration
```

`patient` has its own explicit reconstructable reset plan. Health and Transport do not share a generic table-list YAML.

Both PR Workspace failures occur before Snowflake execution because approved `ci` Snowflake environment configuration/WIF values are still unavailable. They are not reset-contract failures.

## One-click deployment boundary

Current browser UX after a revision is on `main`:

```text
GitHub Actions -> Deploy -> choose dev / uat / prod
```

The shared framework workflow still performs:

```text
verify selected revision is reachable from main
  -> verify exact immutable framework pin
  -> validate metadata
  -> derive database / warehouse / SILVER_STAGING
  -> build bounded dbt vars + config hashes
  -> protected-environment WIF
  -> dbt build
  -> only after success register CONFIG snapshots
```

This is a one-click deployment of the currently selected `main` revision, not yet a complete same-SHA DEV -> UAT -> PROD promotion orchestrator.

## Static proof vs live proof

Static CI proves metadata/schema compatibility, deterministic config hashing, dbt offline parse/render, generation-aware object generation, reset retry guards, forbidden direct shared-control access, bootstrap guards, thin deployment-wrapper boundaries, deployment bundle ordering and generated post-deploy checks.

It does not prove real WIF, Snowflake privilege behavior, `TRUNCATE` grants in a live account, cross-domain denial, transaction/concurrency semantics, real source snapshot/CDC consistency, reset/reload execution, or performance/credits.

## Live blocker and next gate

GitHub `ci` / stable Environments still need real Snowflake values such as:

```text
SNOWFLAKE_ACCOUNT
SNOWFLAKE_OIDC_AUDIENCE
```

Next engineering gate:

```text
merge/rebase stacked PRs in dependency order
  -> bootstrap DEV Snowflake + WIF
  -> Terraform apply platform account/RBAC/database/warehouse objects
  -> render + execute DEV PLATFORM_CONTROL deployment bundle
  -> execute generated verification SQL
  -> prove HEALTH <-> TRANSPORT cross-domain denial
  -> prove normal checkpoint/run/check/config runtime
  -> prove bootstrap fail-closed transitions and atomic handoff
  -> prove Recovery role domain isolation and table TRUNCATE
  -> full reset one DEV dataset
  -> verify generation rollover + old-generation audit retention
  -> run normal main pipeline and verify READY_FOR_INITIAL_LOAD -> ACTIVE
  -> verify completed reset ID reuse fails before cleanup
  -> connect one real/deterministic external-style source
  -> prove snapshot -> incremental/CDC handoff, retry/recovery/reconciliation
  -> then implement exact same-SHA UAT/PROD promotion orchestration
```

## Recommended merge order

```text
1. framework PR #2
2. framework PR #3
3. framework PR #4
4. framework PR #5
5. platform PR #1
6. platform PR #2
7. platform PR #3
8. Transport PR #1
9. Transport PR #2
10. Transport PR #3
11. Transport PR #4
12. Health PR #1
13. Health PR #2
14. Health PR #3
```

Retarget stacked PRs to `main` as lower dependencies merge. Do not claim any source/static object is live-deployed until the DEV bootstrap and live verification gate complete.

## Detailed human docs

```text
PROJECT_BLUEPRINT.md
docs/architecture/ACCOUNT_TOPOLOGY.md
docs/architecture/RBAC_MODEL.md
docs/architecture/OPERATIONAL_CONTROL_ACCESS.md
docs/architecture/BOOTSTRAP_HANDOFF_CONTROL.md
docs/architecture/DATASET_RESET_GENERATION.md
snowflake/control/operations/DEPLOYMENT.md
```
