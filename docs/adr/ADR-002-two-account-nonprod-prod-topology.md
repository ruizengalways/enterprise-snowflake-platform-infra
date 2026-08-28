# ADR-002 — Two-account NONPROD / PROD topology

- **Status:** Accepted
- **Date:** 2026-08-28

## Context

The platform needs personal development, shared development, ephemeral PR CI, UAT, and production while keeping production blast radius and administrative trust separate from day-to-day engineering.

Creating a Snowflake account per lifecycle stage would increase administration and cross-account complexity. Putting all lifecycle stages in one account would weaken the production isolation goal.

## Decision

Use two Snowflake accounts:

```text
NONPROD
├── ANALYTICS_DEV
├── ANALYTICS_CI
├── ANALYTICS_UAT
└── PLATFORM_CONTROL

PROD
├── ANALYTICS_PROD
└── PLATFORM_CONTROL
```

The same project Git history and immutable SHA moves through environments; accounts/databases are deployment targets, not code branches.

Stable project schemas inside shared analytics databases are project-qualified per ADR-016.

`PLATFORM_CONTROL` exists independently in each account so runtime control state does not create a cross-account availability dependency.

## Consequences

- Production has a clear account/security boundary.
- NONPROD can host personal DEV, PR CI and UAT without creating an account per stage.
- Environment configuration must resolve physical database/account targets.
- PROD deployment identity and state must be separately controlled.
- Cross-account observability rollups are optional aggregation, not a runtime prerequisite.
