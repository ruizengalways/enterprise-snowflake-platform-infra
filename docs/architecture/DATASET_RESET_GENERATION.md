# Dataset Full Reset and Generation Lifecycle

## Purpose

Full reset is the fast, pragmatic recovery path for a dataset that is badly wrong and is cheaper to reload from source than to repair in place. A common example is a small dataset feeding an incorrect dashboard where a clean reload is the fastest safe restoration.

Reset is intentionally **not** repair/replay:

```text
REPAIR / REPLAY
  keep the current generation
  keep trusted retained evidence
  recompute selected derived data

FULL RESET
  abandon the current generation
  clear reconstructable domain data
  advance to a new generation
  run the main pipeline as a fresh initial load
```

Repair/replay will remain a separate control/API family.

## Operating model

A dataset has one current lifecycle row:

```text
PLATFORM_CONTROL.OPERATIONS.DATASET_LIFECYCLE
  PROJECT_CODE
  ENVIRONMENT
  DATASET_ID
  CURRENT_GENERATION
  STATE
  LAST_RESET_ID
```

Runtime state is generation-aware:

```text
PIPELINE_CHECKPOINT
PIPELINE_BOOTSTRAP
PIPELINE_RUN
PIPELINE_CHECK_RESULT
```

A full reset does not delete old runtime history. It changes which generation is current.

Example:

```text
vehicle_status

Generation 7
  checkpoints        retained for audit
  bootstrap history  retained for audit
  runs/checks        retained for audit

FULL RESET

Generation 8
  checkpoint         none
  bootstrap           none
  state               READY_FOR_INITIAL_LOAD
```

Current checkpoint/bootstrap domain views resolve generation 8 only. The main pipeline therefore behaves as if this dataset has never been loaded in the current lifecycle.

## Reset state flow

```text
ACTIVE / generation N
  |
  | <DOMAIN>_DATASET_RESET_START
  v
RESETTING / generation N
  |
  | explicit domain cleanup
  | Bronze/Silver/Gold reconstructable tables
  v
<DOMAIN>_DATASET_RESET_COMPLETE
  |
  v
READY_FOR_INITIAL_LOAD / generation N+1
  |
  | manually run the normal main pipeline
  | initial load/bootstrap
  v
ACTIVE / generation N+1
```

For an incremental/bootstrap dataset, the initial bootstrap handoff creates the new-generation checkpoint and completes the reset lifecycle. For a non-checkpoint full-refresh dataset, a successful new-generation pipeline run can complete the lifecycle.

## Failure behavior

Reset is deliberately two-phase.

If data cleanup fails after `RESET_START`:

```text
lifecycle remains RESETTING
normal dataset runs are blocked
old generation history remains intact
cleanup can be retried
RESET_COMPLETE has not advanced the generation
```

This is safer than advancing the generation first and then discovering that half of Bronze/Silver was not cleared.

A reset cannot start while the current generation has a `RUNNING` pipeline attempt.

## Senior Data Engineer+ access

Each domain receives:

```text
AR_<DOMAIN>_RECOVERY
```

This role is intended for Senior Data Engineer+ operators. It is deliberately usable during an incident without a separate multi-person approval workflow.

The capability includes:

```text
READ access to the stable domain database
TRUNCATE on current and future domain TABLES
USAGE on the domain transform warehouse
SELECT/USAGE on the domain-scoped reset views/procedures
```

It does **not** receive:

```text
INSERT / UPDATE / DELETE / OWNERSHIP on domain tables
any direct DML privilege on shared PLATFORM_CONTROL base tables
cross-domain recovery access
```

`AR_<DOMAIN>_ADMIN` inherits the recovery role so there is always an administrative fallback. Senior engineers who need incident recovery can be assigned the recovery role directly through the organization's normal identity/role process; reset does not depend on one named individual being present.

## Domain cleanup ownership

The platform does not guess business table names.

Domain repositories explicitly declare the reconstructable relations for each dataset reset plan. The reusable framework validates that every relation is a fully-qualified Snowflake relation and executes reset step-by-step:

```text
RESET_START
  -> TRUNCATE relation 1
  -> TRUNCATE relation 2
  -> ...
  -> RESET_COMPLETE
```

No generic `reset.objects` YAML language is introduced.

When a dataset gains new downstream materializations, its domain reset plan must be updated at the same time. Stream/Task-specific runtime state, if introduced for that dataset, must likewise be handled explicitly by that implementation rather than hidden in generic reset metadata.

## Audit boundary

Reset clears reconstructable business/derived data for the explicit dataset plan, but preserves platform audit evidence:

```text
KEEP
  DATASET_CONFIG_SNAPSHOT
  old-generation PIPELINE_RUN
  old-generation PIPELINE_CHECK_RESULT
  old-generation PIPELINE_CHECKPOINT
  old-generation PIPELINE_BOOTSTRAP
  DATASET_RESET history

RESET / RECREATE
  explicit Bronze/Silver/Gold tables
  current lifecycle generation
  new-generation checkpoint/bootstrap state
```

`DATASET_RESET.REASON`, requester, timestamps, generation transition, Git SHA and details provide the incident audit trail.

## Live acceptance

Static CI proves generated SQL shape, domain scoping, generation routing, recovery grants and absence of direct shared-control DML. Live DEV must still prove:

```text
reset blocked while a run is RUNNING
RESETTING blocks normal processing
data cleanup failure leaves RESETTING
successful cleanup advances N -> N+1
old generation remains queryable for audit
new generation exposes no checkpoint/bootstrap
main pipeline performs fresh initial load
successful bootstrap/run returns lifecycle to ACTIVE
HEALTH recovery cannot reset TRANSPORT and vice versa
```
