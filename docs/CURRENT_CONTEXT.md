# Current Context — Enterprise Snowflake Hybrid v2

Updated: 2026-09-09

## Canonical architecture

Read `docs/PROJECT_BLUEPRINT.md` for the long-term architecture. The active design is Hybrid Framework v2:

```text
Metadata = HOW TO RUN
SQL      = WHAT THE DATA MEANS

External source -> ingestion -> BRONZE | SILVER -> GOLD
                                      Framework processing starts here
```

No schema-v1 compatibility layer or combined `scd*_merge/snapshot/stream_task` strategy vocabulary remains in the active design.

## Five repositories

Current `main` heads at this handoff:

```text
platform-infra
  550689e0346246af99f630b948669e1a445b98f4
  complete DEV Platform Control v2 deployment-bundle wiring merged

framework
  60ec3c6e29bf66426b6d520f2b7560180b72d149
  post-v2 handoff cleanup on top of the executable v2 baseline

framework executable baseline pinned by domains
  7d3498f8b5ef48d868ea44aade62cf13e50e58f6
  Framework v2 CI #193: SUCCESS

transport
  9fe71b6e1f1979d206c41930aa9479b9af467fc3
  v2 processing-reset contract restored

health
  6274e39f065feb555d5b5d7fc46835c660dbfd55
  v2 processing-reset contract restored

demo-source-systems
  4486109565e79928e65cdce88cbb11ddd7bab52a
  external source-runtime boundary clarified; broad implementation intentionally deferred
```

Transport/Health keep the immutable executable Framework baseline pin `7d3498f8...`; the later Framework `60ec3c6...` commit is documentation-only and does not require a package repin.

## Source/static work now complete

The repository set now contains source/static implementation for:

```text
three-account DEV/UAT/PROD topology
Medallion domain schemas
logical workload -> physical warehouse resolution
human + machine RBAC model
GitHub OIDC / Snowflake WIF identity contracts
cloud-selectable Terraform remote state
schema-v2 project/dataset/raw contracts
offline dbt parse and strategy/materialization routing
SCD1 current-state/tombstone primitive
SCD2 history + sidecar event ledger + affected-key rebuild
Gold Dynamic Table reference path
Framework-free Health/Transport standalone fixtures
domain-scoped runtime/bootstrap/reset/config Platform Control APIs
ordered complete Platform Control deployment bundle
generation-aware processing reset
Transport/Health executable reset wrappers with environment/workspace guards
immutable project/Framework SHA deployment contract
```

Earlier stacked PRs that expressed v1/bootstrap/capture-era design are closed as superseded.

## Processing reset boundary

Full reset is downstream processing recovery, not source deletion.

Transport currently preserves `BRONZE.VEHICLE_STATUS` and clears:

```text
SILVER_CANONICAL.VEHICLE_STATUS_HISTORY
SILVER_CANONICAL.VEHICLE_STATUS_HISTORY__ESF_EVENTS
```

Health preserves `BRONZE.PATIENT` and clears:

```text
SILVER_CANONICAL.PATIENT
```

Old generation control history is retained. If Bronze itself is bad, use a separate ingestion-owned recovery/reland process.

## Platform Control deployment

The DEV workflow now renders `config/environments/dev.yml` into one deterministic deployment bundle containing:

```text
runtime base state
bootstrap state
dataset lifecycle/reset/generation
config snapshot state
domain runtime APIs
domain bootstrap APIs
domain reset APIs
domain config APIs
```

Static CI prevents regression to the old partial four-file deployment. Live deployment has not yet succeeded because DEV Snowflake/WIF environment configuration is not present.

## Open tracking issues

```text
#5 Governance: protect main across all five repositories
#6 Live acceptance: configure DEV WIF and prove Hybrid Framework v2 end to end
```

Issue #5 requires GitHub repository/organization administration permission that the current managed GitHub connection does not expose.

Issue #6 is the authoritative remaining runtime gate.

## Remaining live gate

Next work is infrastructure/runtime proof rather than another metadata redesign:

```text
configure protected DEV GitHub Environment
-> provision/apply Snowflake WIF identities and DEV platform roots
-> deploy the complete PLATFORM_CONTROL bundle
-> prove own-domain access + cross-domain denial
-> prove PR workspace create/drop
-> deploy Transport/Health
-> run live Health SCD1 cases
-> run live Transport SCD2 replay/update/delete/reinsert/late-arrival cases
-> prove Gold Dynamic Table refresh
-> prove generation-aware processing reset
-> run Framework-free standalone live proofs
-> introduce one real external-style source/ingestion path
```

Only after DEV is proven should the exact same-SHA DEV -> UAT -> PROD promotion orchestrator be completed.

## Truth boundary

Static/source CI is strong evidence about schema shape, rendering, parse behavior, deterministic SCD logic and intended grants. It is **not** proof of:

```text
real WIF token exchange
Snowflake owner-rights behavior
live grants/cross-domain denial
transaction/concurrency behavior
live reset/generation rollover
Dynamic Table runtime behavior
external CDC consistency
production cost/performance
```

Do not mark those complete until issue #6 records live run/query evidence.
