# Enterprise Snowflake Platform Infrastructure

Central platform-engineering repository for the Enterprise Snowflake reference platform.

## Start here

For a new conversation/session:

1. [`docs/CURRENT_CONTEXT.md`](docs/CURRENT_CONTEXT.md) — current implementation state, verified CI runs, blockers and next actions.
2. [`docs/PROJECT_BLUEPRINT.md`](docs/PROJECT_BLUEPRINT.md) — canonical long-term architecture.
3. [`docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`](docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md)
4. [`docs/architecture/RBAC_MODEL.md`](docs/architecture/RBAC_MODEL.md)
5. [`docs/architecture/REPOSITORY_LAYOUT.md`](docs/architecture/REPOSITORY_LAYOUT.md)
6. [`docs/standards/TERRAFORM_STANDARDS.md`](docs/standards/TERRAFORM_STANDARDS.md)
7. [`docs/standards/COST_ATTRIBUTION.md`](docs/standards/COST_ATTRIBUTION.md)
8. [`docs/runbooks/terraform-platform-bootstrap.md`](docs/runbooks/terraform-platform-bootstrap.md)

Architecture decisions are under `docs/adr/`.

## Responsibility

This repo owns stable Snowflake platform/account infrastructure: organization/account bootstrap, domain databases/schemas, RBAC, warehouses, Terraform/project machine identities, remote-state adapter contract, workspace permission boundaries, cost/control/governance foundations and `PLATFORM_CONTROL` structure.

It does not own domain business SQL, dbt models, source simulation or day-to-day employee identity membership.

## Current Terraform shape

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
│   ├── workload-identity/
│   └── service-identity/
└── stacks/
    ├── organization/
    ├── identity/{dev,uat,prod}/
    ├── dev/
    ├── project-identity/dev/
    ├── uat/
    └── prod/
```

There are eight independent state/lifecycle boundaries: organization, three platform identities, three platform account states, and DEV project-CI identity.

Execution order in DEV:

```text
organization
-> identity/dev
-> platform/dev
-> project-identity/dev
```

## State backend

Deployment-selectable:

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

OneDrive/SharePoint is for human-facing documents/evidence, not live Terraform state.

## Human access

```text
AR_<DOMAIN>_GUEST -> READER -> DEVELOPER -> ADMIN
DR_<DOMAIN>_ANALYTICS_GUEST -> READ -> WRITE -> OWNER
```

Employees receive roles through enterprise IdP/SCIM. Terraform defines the model, not employee membership.

## DEV workspace access

Personal namespace:

```text
DEV_<DOMAIN>.<DEVELOPER>_<LAYER>
```

CI is machine-only:

```text
SU_GITHUB_<DOMAIN>_CI
  -> AR_<DOMAIN>_CI
      -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> CREATE SCHEMA on CI_<DOMAIN>
      -> WH_<DOMAIN>_CI
```

Current source identities:

```text
SU_GITHUB_HEALTH_CI
SU_GITHUB_TRANSPORT_CI
```

Their GitHub OIDC subjects are pinned to each project repository + Environment `ci`.

## Reusable project PR workflow

The framework repo now provides a pinned reusable PR workspace workflow. Health and Transport contain thin callers.

```text
PR opened/reopened/synchronize -> create PR_<n>_* transient schemas
PR closed                      -> drop PR_<n>_* schemas
```

The workflow requests a short-lived GitHub token using the Snowflake **account-scoped** OIDC audience and authenticates with the domain CI service identity. It currently executes only framework-generated workspace SQL, not arbitrary PR business code.

## Framework metadata contracts

The data-project framework now has versioned schemas + validation for:

```text
project metadata
dataset technical metadata
RAW contract metadata
```

Dataset metadata can declare approved load strategy, standard/custom implementation, keys/watermark/freshness/reconciliation. RAW contracts describe source/entity/grain/columns/CDC/breaking-change policy.

Business joins/calculations/arbitrary SQL are intentionally outside metadata.

See ADR-028.

## Cost attribution

```text
domain storage              -> <ENVIRONMENT>_<DOMAIN>
compute                     -> WH_<DOMAIN>_<WORKLOAD>
query execution attribution -> QUERY_TAG + QUERY_ATTRIBUTION_HISTORY
warehouse idle compute      -> WAREHOUSE_METERING_HISTORY
serverless/ingestion        -> service-specific usage histories
```

Baseline SQL: `snowflake/monitoring/queries/cost_attribution.sql`.

## Current phase

**Phase 1 — Platform Foundation is in progress.**

Source/static-CI proven:

- organization / platform identity / account roots;
- Azure Blob + S3 backend adapters;
- domain human RBAC and warehouses;
- DEV personal workspace + machine-only CI boundaries;
- DEV project CI WIF identity root;
- framework workspace/query-tag utilities;
- framework project/dataset/RAW metadata schemas + validator;
- pinned reusable Health/Transport PR workspace workflows;
- Snowflake-native cost-attribution query baseline.

Still requires live infrastructure: remote state, Snowflake account bootstrap/import, identity/dev + platform/dev apply, project-identity/dev apply, GitHub Environment `ci` configuration, real PR workspace lifecycle test, then UAT/PROD.

Kafka, Snowpipe Streaming and Openflow remain intentionally deferred.
