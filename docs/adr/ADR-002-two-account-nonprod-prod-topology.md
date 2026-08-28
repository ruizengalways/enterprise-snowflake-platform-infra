# ADR-002 — Two-account NONPROD / PROD topology

- **Status:** Superseded by ADR-018
- **Date:** 2026-08-28

## Context

The platform originally selected a two-account `NONPROD` / `PROD` topology to isolate production while keeping development, CI and UAT administratively simple.

## Original decision

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

## Why superseded

Further design work identified two stronger requirements:

1. UAT should exercise account-level security, integrations, parameters and deployment behaviour in a production-like isolation boundary rather than sharing the DEV account.
2. Analytics databases should align with data-product ownership and cost/storage attribution rather than placing all projects in one environment-wide analytics database.

ADR-018 replaces the account topology with `DEV`, `UAT`, and `PROD` accounts. ADR-019 replaces shared environment-wide analytics databases with environment-by-data-product databases.

This file remains in the history to preserve the evolution of the architecture rather than rewriting the earlier decision as if it never existed.
