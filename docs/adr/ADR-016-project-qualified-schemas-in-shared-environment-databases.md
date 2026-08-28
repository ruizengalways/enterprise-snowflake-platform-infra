# ADR-016 — Project-qualified schemas in shared environment databases

- **Status:** Superseded by ADR-019
- **Date:** 2026-08-28

## Context

The earlier architecture used shared environment-wide analytics databases such as `ANALYTICS_DEV`. Project-qualified schema names were introduced to prevent Health/Transport collisions inside those shared databases.

## Original decision

Stable project schemas used `<PROJECT>_<LAYER>`, personal schemas used `<DEVELOPER>_<PROJECT>_<LAYER>`, and PR schemas used `<PROJECT>_PR_<NUMBER>_<LAYER>`.

## Why superseded

The database boundary has now moved to environment × data product, for example `DEV_HEALTH`, `UAT_HEALTH`, and `PROD_TRANSPORT`. The database name itself supplies the project namespace, so repeating the project in every stable schema adds noise without adding isolation.

ADR-019 defines the replacement database and schema naming model. This ADR remains for architectural history.
