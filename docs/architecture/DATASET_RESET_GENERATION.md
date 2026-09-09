# Dataset Processing Reset and Generation Lifecycle

## Purpose

A full **processing reset** is the fast recovery path for a dataset whose Silver/Gold state is badly wrong but whose landed Bronze evidence is still trusted.

Reset is intentionally distinct from repair/replay and from source re-ingestion:

```text
REPAIR / REPLAY
  keep the current generation
  keep trusted Bronze evidence
  recompute selected derived data

PROCESSING RESET
  abandon the current processing generation
  preserve Bronze evidence
  clear explicit reconstructable Silver/Gold state
  advance to a new generation
  run the normal processing pipeline as a fresh initial load

SOURCE / INGESTION RESET
  separate concern
  owned by the ingestion implementation
  not implied by the Framework recovery role
```

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

Framework runtime state is generation-aware:

```text
PIPELINE_CHECKPOINT
PIPELINE_BOOTSTRAP
PIPELINE_RUN
PIPELINE_CHECK_RESULT
```

These are processing-control records, not copies of source-connector offsets/cursors.

A processing reset does not delete old runtime history. It changes which generation is current.

Example:

```text
vehicle_status

Generation 7
  processing checkpoints  retained for audit
  bootstrap history       retained for audit
  runs/checks             retained for audit
  Bronze evidence         preserved

PROCESSING RESET

Generation 8
  processing checkpoint   none
  bootstrap               none
  state                   READY_FOR_INITIAL_LOAD
  Bronze evidence         still present
```

Current checkpoint/bootstrap domain views resolve generation 8 only. The processing pipeline therefore behaves as if the dataset has not yet been built in the current generation, while retained Bronze allows deterministic reconstruction.

## Reset state flow

```text
ACTIVE / generation N
  |
  | <DOMAIN>_DATASET_RESET_START
  v
RESETTING / generation N
  |
  | explicit domain cleanup
  | Silver/Gold reconstructable tables only
  | Bronze remains untouched
  v
<DOMAIN>_DATASET_RESET_COMPLETE
  |
  v
READY_FOR_INITIAL_LOAD / generation N+1
  |
  | run the normal processing pipeline
  | optional processing bootstrap from preserved Bronze
  v
ACTIVE / generation N+1
```

For an incremental dataset that uses processing bootstrap, the new-generation handoff creates the new processing checkpoint. For a dataset that does not use a processing checkpoint, a successful new-generation pipeline run can complete the lifecycle.

## Failure behavior

Reset is deliberately two-phase.

If data cleanup fails after `RESET_START`:

```text
lifecycle remains RESETTING
normal dataset runs are blocked
old generation history remains intact
Bronze evidence remains intact
cleanup can be retried
RESET_COMPLETE has not advanced the generation
```

A reset cannot start while the current generation has a `RUNNING` pipeline attempt.

## Recovery access

Each domain receives:

```text
AR_<DOMAIN>_RECOVERY
```

The role is intended for governed senior-engineer incident recovery and is inherited by the domain ADMIN role.

Its baseline capability is:

```text
READ on the stable domain database, including Bronze
TRUNCATE on current/future tables in reconstructable Silver/Gold schemas only
USAGE on the domain transform warehouse
SELECT/USAGE on the domain-scoped reset views/procedures
```

It does **not** receive:

```text
TRUNCATE on BRONZE
TRUNCATE on DQ by default
INSERT / UPDATE / DELETE / OWNERSHIP on domain tables
any direct DML on shared PLATFORM_CONTROL base tables
cross-domain recovery access
```

This keeps the destructive capability aligned with the processing boundary. Re-ingestion or destructive source-evidence maintenance requires a separately designed ingestion capability.

## Domain cleanup ownership

The platform does not guess business table names.

Domain repositories explicitly declare the reconstructable relations for each dataset reset operation. The reusable Framework validates each fully qualified relation and executes the reset lifecycle around those explicit operations:

```text
RESET_START
  -> TRUNCATE explicit reconstructable relation 1
  -> TRUNCATE explicit reconstructable relation 2
  -> ...
  -> RESET_COMPLETE
```

No generic `reset.objects` YAML language is introduced.

The v2 domain reset wrappers must not include Bronze relations. When a dataset gains new Silver/Gold materializations or sidecar state such as the SCD2 `__ESF_EVENTS` ledger, its domain reset plan must be updated at the same time.

Views and derived Dynamic Tables are rebuilt/refreshed through normal deployment/processing rather than being blindly truncated.

## Audit boundary

Processing reset clears explicit reconstructable downstream data but preserves both landed evidence and platform audit evidence:

```text
KEEP
  BRONZE source-faithful evidence
  DATASET_CONFIG_SNAPSHOT
  old-generation PIPELINE_RUN
  old-generation PIPELINE_CHECK_RESULT
  old-generation PIPELINE_CHECKPOINT
  old-generation PIPELINE_BOOTSTRAP
  DATASET_RESET history

RESET / REBUILD
  explicit Silver/Gold tables and processing sidecars
  current lifecycle generation
  new-generation processing checkpoint/bootstrap state
```

`DATASET_RESET.REASON`, requester, timestamps, generation transition, Git SHA, and details provide the incident audit trail.

## Live acceptance

Static CI can prove generated SQL shape, domain scoping, generation routing, recovery grants, and absence of direct shared-control DML. Live DEV must still prove:

```text
reset blocked while a run is RUNNING
RESETTING blocks normal processing
cleanup failure leaves RESETTING
Bronze cannot be truncated by AR_<DOMAIN>_RECOVERY
successful cleanup advances N -> N+1
old generation remains queryable for audit
new generation exposes no current processing checkpoint/bootstrap
main pipeline rebuilds Silver/Gold from preserved Bronze
successful bootstrap/run returns lifecycle to ACTIVE
HEALTH recovery cannot reset TRANSPORT and vice versa
```
