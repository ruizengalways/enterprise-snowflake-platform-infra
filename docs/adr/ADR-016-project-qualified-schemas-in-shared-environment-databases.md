# ADR-016 — Project-qualified schemas in shared environment databases

- **Status:** Accepted
- **Date:** 2026-08-28

## Context

`ANALYTICS_DEV`, `ANALYTICS_CI`, and `ANALYTICS_UAT` are shared environment databases that host more than one data project. The earlier shorthand names `STAGING`, `ALICE_STAGING`, and `PR_123_STAGING` are ambiguous in a multi-repository platform:

- Health and Transport would compete for the same stable schema names.
- Pull-request numbers are repository-local, so `PR_123_*` can exist simultaneously in multiple repositories.
- Personal developer schemas need to identify both the developer and project.

## Decision

All project-owned schemas in shared analytics databases include the project code.

Stable project schemas:

```text
<PROJECT>_<LAYER>
```

Examples:

```text
HEALTH_STAGING
HEALTH_INTERMEDIATE
HEALTH_CANONICAL
HEALTH_MARTS
HEALTH_SEMANTIC

TRANSPORT_STAGING
TRANSPORT_INTERMEDIATE
TRANSPORT_CANONICAL
TRANSPORT_MARTS
TRANSPORT_SEMANTIC
```

Personal DEV schemas:

```text
<DEVELOPER>_<PROJECT>_<LAYER>
```

Example: `ALICE_HEALTH_STAGING`.

Ephemeral PR CI schemas:

```text
<PROJECT>_PR_<NUMBER>_<LAYER>
```

Example: `TRANSPORT_PR_123_STAGING`.

`PLATFORM_CONTROL` is a dedicated database and keeps its fixed control schema names (`DEPLOYMENT`, `QUALITY`, `OBSERVABILITY`, `OPERATIONS`) because those schemas are not shared project namespaces.

## Consequences

- Health and Transport can coexist safely in the same environment database.
- Repository-local PR numbers cannot collide across projects.
- dbt schema-generation macros must include project scope in Phase 2.
- Project code becomes required platform metadata.
- Environment names remain outside dbt model SQL; schema naming is resolved by configuration/macros.
