# ADR-020 — Domain guest access and workload warehouses

- **Status:** Accepted; UAT/PROD transform execution detail amended by ADR-034
- **Date:** 2026-08-29

## Context

The platform needs clear domain isolation for Health, Transport, and future data products. A single generic reader role is too broad for business consumers because internal layers such as STAGING and CANONICAL may expose implementation detail or data that is not consumer-ready.

Cost attribution also should not depend on database-per-source. Compute needs a stable domain/workload boundary that can be measured independently.

## Decision

Every governed domain receives an independent account-role hierarchy:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

Every domain database receives:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
  -> DR_<DOMAIN>_ANALYTICS_READ
  -> DR_<DOMAIN>_ANALYTICS_WRITE
  -> DR_<DOMAIN>_ANALYTICS_OWNER
```

`GUEST` is authenticated read-only consumer access. It receives only database USAGE, published-schema USAGE, and SELECT on current/future tables, views, and semantic views in configured published schemas. Initial published schemas are `MARTS` and `SEMANTIC`.

`READER` can inspect all stable domain layers. `DEVELOPER` receives WRITE only in the DEV account. UAT/PROD developers remain read-only by default.

Each domain receives separate workload warehouses:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
```

DEV additionally receives `WH_<DOMAIN>_CI`. The account already identifies the environment, so ordinary warehouse names do not repeat DEV/UAT/PROD.

GUEST receives QUERY; READER inherits it. DEV DEVELOPER receives TRANSFORM. CI warehouses are machine-only.

For stable automated delivery, ADR-034 adds the independent machine role `AR_<DOMAIN>_DEPLOY`, which receives `WH_<DOMAIN>_TRANSFORM` in DEV/UAT/PROD. The earlier transitional UAT/PROD ADMIN -> TRANSFORM grant is no longer part of the baseline. Human UAT/PROD emergency transform execution is JIT/break-glass through enterprise identity governance rather than a permanent Terraform grant.

## Consequences

- Business/guest consumers do not automatically see internal transformation layers.
- Health authority never implies Transport authority and vice versa.
- Query and transformation compute can be attributed by domain/workload without creating database-per-source.
- Role/warehouse naming remains stable across the three accounts.
- Future projects such as Finance can be onboarded by adding a domain code, project databases, and the same role/warehouse pattern.
- Published schema policy becomes explicit environment metadata and can evolve without redefining the role hierarchy.
- Routine UAT/PROD transformation compute is owned by project deployment automation, not a standing human ADMIN grant.
