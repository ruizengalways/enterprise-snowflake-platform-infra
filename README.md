# Enterprise Snowflake Platform Infrastructure

Central platform-engineering repository for the Enterprise Snowflake reference platform.

## Start here

For a new ChatGPT/session handoff, read in this order:

1. [`docs/CURRENT_CONTEXT.md`](docs/CURRENT_CONTEXT.md) — current implementation state, decisions, blockers and next actions.
2. [`docs/PROJECT_BLUEPRINT.md`](docs/PROJECT_BLUEPRINT.md) — canonical long-term architecture.
3. [`docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`](docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md)
4. [`docs/architecture/ACCOUNT_TOPOLOGY.md`](docs/architecture/ACCOUNT_TOPOLOGY.md)
5. [`docs/architecture/RBAC_MODEL.md`](docs/architecture/RBAC_MODEL.md)
6. [`docs/architecture/REPOSITORY_LAYOUT.md`](docs/architecture/REPOSITORY_LAYOUT.md)
7. [`docs/standards/TERRAFORM_STANDARDS.md`](docs/standards/TERRAFORM_STANDARDS.md)
8. [`docs/standards/COST_ATTRIBUTION.md`](docs/standards/COST_ATTRIBUTION.md)
9. [`docs/runbooks/terraform-platform-bootstrap.md`](docs/runbooks/terraform-platform-bootstrap.md)

Architecture decisions are under `docs/adr/`.

## Repository responsibility

This repository owns Snowflake account/platform foundation: organization bootstrap, DEV/UAT/PROD topology, domain databases, stable structural schemas, domain/platform RBAC, domain warehouses, Terraform machine identity, remote-state adapter contract, workspace access boundaries, cost-attribution platform conventions, `PLATFORM_CONTROL`, governance/observability/recovery foundations.

It does not own Health/Transport business SQL, project dbt models, shared dbt/framework mechanics, source simulation, or day-to-day employee identity membership.

## Terraform foundation

```text
terraform/
├── backend-profiles/{azurerm,s3}/
├── scripts/select-backend.sh
├── modules/
│   ├── analytics-environment/
│   ├── warehouse/
│   ├── platform-control/
│   ├── rbac/
│   ├── workspace-access/
│   └── workload-identity/
└── stacks/
    ├── organization/
    ├── identity/{dev,uat,prod}/
    ├── dev/
    ├── uat/
    └── prod/
```

`organization/` alone uses ORGADMIN. `identity/<env>/` bootstraps `SU_GITHUB_TERRAFORM_<ENV> -> AR_TERRAFORM_<ENV>`. Routine account roots use those machine roles rather than system roles.

Static CI validates all seven roots plus Azure Blob and S3 backend profiles.

## State and machine authentication

State backend is deployment-selectable:

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

The Snowflake Terraform code is identical for both. GitHub OIDC authenticates to the chosen state provider and independently to Snowflake WIF.

OneDrive/SharePoint may store human-facing docs/evidence, not live Terraform state.

## Domain access and compute

Stable human access:

```text
AR_<DOMAIN>_GUEST -> READER -> DEVELOPER -> ADMIN
DR_<DOMAIN>_ANALYTICS_GUEST -> READ -> WRITE -> OWNER
```

Compute:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
```

Employees receive domain roles through enterprise IdP/SCIM; Terraform defines the model, not employee membership.

## DEV personal and PR CI workspaces

Human roles attach only to `DEV_<DOMAIN>` databases. DEV WRITE roles receive `CREATE SCHEMA` so developers can use:

```text
<DEVELOPER>_<LAYER>
```

This is a namespace convention, not per-person security isolation.

CI is machine-only:

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
  -> CREATE SCHEMA on CI_<DOMAIN>
  -> WH_<DOMAIN>_CI
```

Human GUEST/READER/DEVELOPER/ADMIN roles do not attach to CI databases.

PR schemas follow `PR_<NUMBER>_<LAYER>`. Reusable guarded SQL rendering lives in `enterprise-snowflake-data-project-framework`; PR workspaces are transient/reproducible and explicitly cleaned up.

## Cost attribution

Use complementary boundaries rather than database-per-source:

```text
domain storage              -> <ENVIRONMENT>_<DOMAIN>
compute                     -> WH_<DOMAIN>_<WORKLOAD>
query execution attribution -> JSON QUERY_TAG + QUERY_ATTRIBUTION_HISTORY
warehouse idle compute      -> WAREHOUSE_METERING_HISTORY
serverless/ingestion        -> service-specific usage history
```

Baseline queries live at:

```text
snowflake/monitoring/queries/cost_attribution.sql
```

Shared query-tag construction lives in the framework repo. See `docs/standards/COST_ATTRIBUTION.md` and ADR-026.

## Current phase

**Phase 1 — Platform Foundation is in progress.**

Source/static-CI proven now includes:

- pinned Terraform/provider versions and committed lock files;
- organization + per-account Terraform identity roots;
- Azure Blob/S3 backend adapters;
- three-account/domain infrastructure;
- human GUEST/READER/DEVELOPER/ADMIN RBAC;
- metadata-driven domain warehouse grants;
- DEV personal workspace `CREATE SCHEMA` capability;
- machine-only `AR_<DOMAIN>_CI` / `DR_<DOMAIN>_CI_WORKSPACE` boundaries;
- framework workspace/query-tag utilities with passing Python CI;
- Snowflake-native cost-attribution query baseline.

Still not executed against live infrastructure: real remote state, Snowflake account bootstrap/import, identity apply, DEV remote plan/apply, effective privilege verification, project-CI service identities, UAT/PROD rollout. Resource monitors/budgets and persisted observability views are also still pending.

Kafka, Snowpipe Streaming, Openflow and broad dbt modelling remain intentionally deferred.
