# ADR-018 — Three-account DEV / UAT / PROD topology

- **Status:** Accepted
- **Date:** 2026-08-28
- **Supersedes:** ADR-002

## Context

The platform needs personal/shared development, ephemeral PR CI, production-like UAT, and production. The original two-account design placed DEV, CI and UAT together in NONPROD.

That is simple, but UAT cannot prove account-level behaviour if it shares the same account boundary as development. Account-scoped RBAC, integrations, account parameters, workload identities, network/security controls and operational settings should be testable before production.

A dedicated CI account would add a fourth account without enough benefit for this project because PR CI is deliberately ephemeral and can remain isolated through project-specific CI databases, schemas, warehouses and machine identities.

## Decision

Use three Snowflake accounts:

```text
Snowflake Organization
├── DEV account
│   ├── DEV_HEALTH
│   ├── CI_HEALTH
│   ├── DEV_TRANSPORT
│   ├── CI_TRANSPORT
│   └── PLATFORM_CONTROL
│
├── UAT account
│   ├── UAT_HEALTH
│   ├── UAT_TRANSPORT
│   └── PLATFORM_CONTROL
│
└── PROD account
    ├── PROD_HEALTH
    ├── PROD_TRANSPORT
    └── PLATFORM_CONTROL
```

DEV and PR CI share the DEV account but use separate project databases and warehouses. UAT and PROD are independent accounts.

Each account has its own Terraform root stack, state boundary and eventual workload identity. `PLATFORM_CONTROL` remains account-local.

## Promotion path

```text
personal/shared DEV
-> ephemeral PR CI (DEV account)
-> UAT account
-> PROD account
```

The exact same immutable Git SHA is promoted. Accounts are deployment targets, not Git branches.

## Account creation boundary

The account root stacks assume their target account already exists. Snowflake provider `2.19.0` supports the `snowflake_account` resource, but creating accounts requires organization-level privilege (`ORGADMIN`) and initial administrator material. Account creation therefore belongs to a separate, narrowly privileged organization bootstrap lifecycle rather than the routine DEV/UAT/PROD stacks.

No `ORGADMIN` or `ACCOUNTADMIN` credential is placed in normal project CI.

## Consequences

- UAT can validate account-level configuration before PROD.
- Production remains isolated from engineering activity.
- CI remains cost-effective without introducing a fourth account.
- Terraform now has three account stacks and eventually three independent remote-state/workload-identity boundaries.
- Platform configuration duplicated across accounts must be expressed through shared modules and metadata, not copy/pasted business logic.
- Cross-account promotion/data movement must be explicit where needed.
