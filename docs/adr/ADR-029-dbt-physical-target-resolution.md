# ADR-029 — dbt Physical Target Resolution

## Status

Accepted — 2026-08-29

## Context

Domain model SQL must not hard-code Snowflake environment names such as `DEV_HEALTH`, `CI_HEALTH`, `UAT_HEALTH`, or `PROD_HEALTH`. The platform already has deterministic database, warehouse, personal-workspace, and PR-workspace naming rules. Re-implementing those rules independently in every dbt project would create drift.

At the same time, environment routing must remain simple and inspectable; it must not become a second orchestration language encoded in YAML.

## Decision

The shared data-project framework owns deterministic dbt physical-target resolution.

Current stable dbt reference versions are pinned to:

```text
dbt-core      1.12.3
dbt-snowflake 1.12.0
```

The resolver accepts only stable technical inputs:

```text
project_code
environment = dev | ci | uat | prod
workload    = query | transform | ci
optional developer identity for personal DEV
optional PR number for CI
```

It derives:

```text
DBT_DATABASE
DBT_WAREHOUSE
DBT_DEFAULT_SCHEMA
ESF_SCHEMA_PREFIX
ESF_ENVIRONMENT
ESF_PROJECT_CODE
```

Canonical mapping:

```text
DEV shared        -> DEV_<DOMAIN> / WH_<DOMAIN>_<QUERY|TRANSFORM> / stable layer schemas
DEV personal      -> DEV_<DOMAIN> / WH_<DOMAIN>_<QUERY|TRANSFORM> / <DEVELOPER>_<LAYER>
PR CI             -> CI_<DOMAIN>  / WH_<DOMAIN>_CI                / PR_<NUMBER>_<LAYER>
UAT               -> UAT_<DOMAIN> / WH_<DOMAIN>_<QUERY|TRANSFORM> / stable layer schemas
PROD              -> PROD_<DOMAIN>/ WH_<DOMAIN>_<QUERY|TRANSFORM> / stable layer schemas
```

The Python resolver is the authoritative naming/validation implementation. The reusable dbt package exposes thin macros that consume resolved environment variables. Each domain root project keeps only explicit wrapper macros delegating to the pinned framework package.

Project `profiles.yml` files contain no passwords/private keys and read account/user/role/target values from environment variables. CI workload identity uses the Snowflake adapter's `workload_identity` authenticator with provider `OIDC` and a short-lived token supplied immediately before dbt execution.

Model SQL should use dbt `ref()` / `source()` and layer configuration; it should not contain physical DEV/UAT/PROD database names.

## Versioning

Domain projects pin an immutable framework revision in `dbt/packages.yml` and pin reusable GitHub Actions by commit SHA. Framework upgrades are deliberate changes, not implicit `main` drift.

The current reference does not adopt dbt Core/Fusion 2.x pre-release behavior. A future engine/version change requires compatibility review and CI proof before becoming canonical.

## Verification

Framework CI installs the pinned dbt versions, resolves a CI target, runs `dbt deps` and offline `dbt parse`, then inspects `manifest.json` to prove a model resolves to the expected physical database/schema.

Health and Transport also use a reusable static dbt validation action that installs the pinned versions and parses their checked-in dbt project without connecting to Snowflake.

Static parse validates configuration/macros/dependencies only; it does not prove live Snowflake WIF, grants, or runtime SQL behavior.

## Consequences

Positive:

- project SQL is environment-agnostic;
- adding a domain follows the same resolver rather than copying environment logic;
- personal DEV and PR CI naming is consistent with platform RBAC/workspace rules;
- dbt engine/adapter compatibility is explicit and testable;
- project repos remain thin.

Trade-offs:

- project wrappers still exist because root-project dbt naming overrides should be explicit;
- CI must mint short-lived OIDC tokens close to dbt execution;
- changing platform naming conventions requires a versioned framework change and project upgrade.
