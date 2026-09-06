# Enterprise Snowflake Platform — Current Context

Concise human handoff for a new conversation. Detailed architecture belongs in linked docs; machine truth belongs in Terraform/config/schema/SQL/tests.

## Current phase

The source/static foundation now includes domain-scoped runtime/bootstrap control, Medallion database topology, Git-owned dataset configuration snapshots, metadata-driven SCD1/SCD2, and statically protected thin domain deployment wrappers.

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
head 1b838965ab77a5d23597c54c93a075c154e30da0
```

It provides domain-scoped `OPERATIONS` surfaces for checkpoint, run, quality-result and bootstrap state. Project roles receive only generated domain views/procedures, never direct shared-table DML. Bootstrap enforces explicit reconciliation success, checkpoint-regression denial and atomic handoff commit.

Platform PR #2 is stacked on PR #1:

```text
feature/medallion-dataset-control-plane
verified implementation head a086401844d764dee1ef8e8053abe73855878b6e
Terraform CI: SUCCESS
Platform Control SQL CI: SUCCESS
```

It adds Medallion schemas plus:

```text
PLATFORM_CONTROL.CONFIG.DATASET_CONFIG_SNAPSHOT
<DOMAIN>_DATASET_CONFIG_SNAPSHOT
<DOMAIN>_REGISTER_DATASET_CONFIG_SNAPSHOT
```

Same project/environment/dataset/Git-SHA + same content is idempotent. Reusing the same Git SHA with conflicting config fails closed. Deployment bundle and post-deploy verification include both OPERATIONS and CONFIG surfaces.

## Framework baseline

Verified framework implementation/domain pin:

```text
02e3fca78b453e8a39a1722ce96b15dfc98d7cf8
Framework CI #175: SUCCESS
Bootstrap Contract CI #7: SUCCESS
```

Framework PR stack:

```text
PR #2 metadata-driven SCD2
  -> PR #3 bootstrap handoff
      -> PR #4 Medallion + config snapshot + stable deployment
```

Framework supports independent capture and target/history strategies, explicit `scd1_merge`, metadata-driven SCD2, deterministic config hashes and post-build CONFIG registration. Later framework branch commits may be documentation-only; domain repos should not repin merely because handoff prose changed.

## Domain consumer stack

Transport:

```text
PR #1 domain runtime + vehicle_status SCD2
PR #2 bootstrap handoff
PR #3 Medallion/config audit/thin Deploy wrapper
verified source/static head b771d036d162a983342344557f37f96e914126b1
Metadata CI #36: SUCCESS
dbt Static CI #46: SUCCESS
PR Workspace #27: blocked before Snowflake execution by missing ci WIF configuration
```

`vehicle_status` is the standard SCD2 reference. `vehicle_position` remains an append/event dataset, not SCD2.

Health:

```text
PR #1 domain runtime proof
PR #2 Medallion/config audit/thin Deploy wrapper
verified source/static head 0c70e34930131191f53af0bbb4654a91554b2067
Metadata CI #18: SUCCESS
dbt Static CI #27: SUCCESS
PR Workspace #8: blocked before Snowflake execution by missing ci WIF configuration
```

Health `patient` is intentionally `scd1_merge`: its current RAW reference contract does not declare real business attributes suitable for SCD2 tracking. Transport remains the SCD2 reference rather than fabricating Health tracked columns for symmetry.

Both domain static suites now protect the Deploy wrapper contract: no manual `git_sha` input, approved immutable framework pin, `github.sha` handoff, and no copied OIDC/token logic in the domain repo.

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

This is already a one-click deployment of the currently selected `main` revision. It is **not yet a complete same-SHA cross-environment promotion orchestrator**. If `main` advances after DEV, a later UAT/PROD run from newer `main` would use another SHA. Do not call that promotion of the DEV release.

The target remains:

```text
same immutable SHA
DEV -> UAT -> PROD
```

After live DEV is proven, add release/promotion orchestration that carries forward the exact deployed SHA (for example through an immutable release ref or deployment record) without introducing environment source branches.

## Static proof vs live proof

Static CI proves metadata/schema compatibility, deterministic config hashing, dbt offline parse/render, domain object generation, forbidden direct base-table access, bootstrap guards, thin deployment-wrapper boundaries, deployment bundle ordering and generated post-deploy checks.

It does not prove real WIF, Snowflake privilege behavior, cross-domain denial, transaction/concurrency semantics, real source snapshot/CDC consistency, retries/recovery or performance/credits.

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
  -> prove checkpoint/run/check/config runtime
  -> prove bootstrap fail-closed transitions and atomic handoff
  -> one-click deploy one domain current-main revision to DEV
  -> verify DATASET_CONFIG_SNAPSHOT audit
  -> connect one real/deterministic external-style source
  -> prove snapshot -> incremental/CDC handoff, retry/recovery/reconciliation
  -> then implement exact same-SHA UAT/PROD promotion orchestration
```

## Recommended merge order

```text
1. framework PR #2
2. framework PR #3
3. framework PR #4
4. platform PR #1
5. platform PR #2
6. Transport PR #1
7. Transport PR #2
8. Transport PR #3
9. Health PR #1
10. Health PR #2
```

Retarget stacked PRs to `main` as lower dependencies merge. Do not claim any source/static object is live-deployed until the DEV bootstrap and live verification gate complete.

## Detailed human docs

```text
PROJECT_BLUEPRINT.md
docs/architecture/ACCOUNT_TOPOLOGY.md
docs/architecture/RBAC_MODEL.md
docs/architecture/OPERATIONAL_CONTROL_ACCESS.md
docs/architecture/BOOTSTRAP_HANDOFF_CONTROL.md
snowflake/control/operations/DEPLOYMENT.md
```
