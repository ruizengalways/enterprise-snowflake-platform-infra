# ADR-001 — Five-repository architecture

- **Status:** Accepted
- **Date:** 2026-08-28

## Context

The platform needs clear ownership boundaries between central Snowflake platform engineering, reusable data-project framework code, source-system simulation, and domain-specific data products. Shared framework fixes must not require manual edits in every project repository.

## Decision

Use five repositories:

1. `enterprise-snowflake-platform-infra` — central platform foundation and canonical architecture documentation.
2. `enterprise-snowflake-data-project-framework` — versioned reusable golden-path capabilities.
3. `enterprise-snowflake-demo-source-systems` — deterministic source-system simulation only.
4. `enterprise-snowflake-health-analytics` — Health-specific contracts/configuration/business logic.
5. `enterprise-snowflake-transport-analytics` — Transport-specific contracts/configuration/business logic.

Project repositories consume framework capabilities through versioned dependencies rather than permanent copy/paste.

## Consequences

- Cross-project technical behaviour has an explicit home.
- Domain repositories remain thin and independently releasable.
- Platform infrastructure changes do not become mixed with domain transformation changes.
- The demo source repository remains outside the downstream Snowflake data-platform boundary.
- Cross-repository version compatibility must be managed explicitly.