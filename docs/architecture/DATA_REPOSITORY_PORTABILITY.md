# Data repository portability

## Decision

Domain data repositories are **not hosted by the enterprise data framework**.

Each domain repository must have a framework-independent portable core that remains useful on any Snowflake platform.

At minimum, a repository must be able to expose its source contracts and generate representative synthetic source data without installing the enterprise framework.

## Dependency direction

```text
portable domain repository core
  contracts
  domain-owned metadata
  synthetic Snowflake SQL
  domain documentation
           ↑
optional enterprise adapter
  dbt/platform integration
  control-plane calls
  deployment wrappers
           ↑
enterprise framework + platform infra
```

The enterprise framework may consume/wrap a domain repository. The domain portable core must not require the framework to exist.

## Portable-core rules

Portable source/demo functionality must not assume:

- `PLATFORM_CONTROL`;
- enterprise Terraform;
- `AR_<DOMAIN>_*` roles;
- enterprise warehouse names;
- `<ENV>_<DOMAIN>` databases;
- GitHub WIF;
- DEV/UAT/PROD account topology;
- a custom dbt package.

A caller should be able to select an arbitrary Snowflake database/warehouse, run ordinary SQL, and create the repository's demo schema/data with normal object-creation privileges.

## Domain ownership

Source contract shape and domain meaning belong in the domain repository.

Framework/platform repositories may provide reusable behavior for:

```text
Medallion deployment
checkpoint/bootstrap
SCD helpers
config audit
reset/generation
RBAC/WIF
promotion
```

They must not become the only place where a domain's source shape can be understood or generated.

## Current reference consumers

Transport PR #5 adds a pure-Snowflake `DEMO_TRANSPORT` generator for `vehicle_status` CDC and `vehicle_position` events.

Health PR #4 adds a pure-Snowflake `DEMO_HEALTH` generator for `patient` CDC plus explicitly synthetic-only descriptive profile data.

Each repo has a `Standalone SQL CI` that runs without the enterprise framework and checks for forbidden enterprise-platform coupling.

## Acceptance

Static acceptance:

```text
standalone CI succeeds
no enterprise-framework/platform references in standalone SQL
contract columns are present
```

Live portability acceptance:

```text
plain Snowflake account/database
no PLATFORM_CONTROL
no enterprise framework/dbt package
no enterprise roles/warehouses required
    -> execute standalone SQL
    -> validate expected synthetic row counts and keys
```

Enterprise-platform live acceptance remains a separate concern.
