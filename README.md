# Enterprise Snowflake Platform Infrastructure

Central platform-engineering repository for the Enterprise Snowflake reference platform.

## Start here

For a new conversation/session, read in this order:

1. [`docs/CURRENT_CONTEXT.md`](docs/CURRENT_CONTEXT.md) — current implementation state, verified CI, blockers and next actions.
2. [`docs/PROJECT_BLUEPRINT.md`](docs/PROJECT_BLUEPRINT.md) — canonical long-term architecture.
3. [`docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`](docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md)
4. [`docs/architecture/ACCOUNT_TOPOLOGY.md`](docs/architecture/ACCOUNT_TOPOLOGY.md)
5. [`docs/architecture/RBAC_MODEL.md`](docs/architecture/RBAC_MODEL.md)
6. [`docs/architecture/REPOSITORY_LAYOUT.md`](docs/architecture/REPOSITORY_LAYOUT.md)
7. [`docs/standards/TERRAFORM_STANDARDS.md`](docs/standards/TERRAFORM_STANDARDS.md)
8. [`docs/runbooks/terraform-platform-bootstrap.md`](docs/runbooks/terraform-platform-bootstrap.md)

Architecture decisions are under `docs/adr/`.

## Responsibility

This repo owns stable Snowflake platform/account infrastructure: organization/account bootstrap, domain databases/schemas, RBAC, warehouses, Terraform and project workload identities, remote-state adapter contracts, workspace/deployment permission boundaries, cost/governance foundations and structural `PLATFORM_CONTROL` lifecycle.

It does not own domain business SQL, dbt models, source simulation, ingestion producer code or day-to-day employee identity membership.

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
    ├── uat/
    ├── prod/
    └── project-identity/{dev,uat,prod}/
```

There are ten independent state/lifecycle boundaries:

```text
organization
identity/dev
identity/uat
identity/prod
platform/dev
platform/uat
platform/prod
project-identity/dev
project-identity/uat
project-identity/prod
```

Per-environment dependency is:

```text
identity/<env>
  -> platform/<env>
      -> project-identity/<env>
```

## State backend

Deployment-selectable:

```text
azurerm -> Azure Blob Storage (Microsoft-first reference)
s3      -> Amazon S3 (AWS alternative)
```

One deployment uses one authoritative writable backend. OneDrive/SharePoint is for human-facing documents/evidence, not live Terraform state.

## Human and machine access

Human domain hierarchy:

```text
AR_<DOMAIN>_GUEST -> READER -> DEVELOPER -> ADMIN
DR_<DOMAIN>_ANALYTICS_GUEST -> READ -> WRITE -> OWNER
```

Employees receive roles through enterprise IdP/SCIM. Terraform defines the permission model, not employee membership.

Machine roles are separate:

```text
AR_<DOMAIN>_CI       # DEV PR workspace lifecycle only
AR_<DOMAIN>_DEPLOY   # stable DEV/UAT/PROD project delivery
```

UAT/PROD human roles receive no permanent transform warehouse grant in the baseline. Emergency manual execution is JIT/break-glass through enterprise identity governance.

## Project workload identities

DEV PR CI:

```text
SU_GITHUB_<DOMAIN>_CI -> AR_<DOMAIN>_CI
```

Stable project delivery in DEV/UAT/PROD:

```text
SU_GITHUB_<DOMAIN>_DEPLOY -> AR_<DOMAIN>_DEPLOY
```

All project workload identities use GitHub OIDC + Snowflake Workload Identity Federation with repository + GitHub Environment scoped subjects and an account-scoped audience.

## Reusable project workflows

The framework repo owns reusable PR workspace and stable project deployment workflows. Health and Transport contain thin callers pinned to an immutable framework SHA.

PR workspace lifecycle:

```text
PR opened/reopened/synchronize -> create PR_<n>_* transient schemas
PR closed                      -> guarded drop of PR_<n>_* schemas
```

Stable deployment requires a full project Git SHA and full framework Git SHA. The reusable workflow verifies the target project commit belongs to `main` history, checks out the exact revision, verifies the project dbt package pin matches the framework revision, and targets the selected protected GitHub Environment.

Promotion is therefore:

```text
same project SHA
DEV -> UAT -> PROD
```

No environment branches are used.

## Platform and framework status

Source/static CI currently proves:

- organization, platform identity, platform account and project-identity Terraform roots;
- Azure Blob + S3 backend adapters;
- domain human RBAC, PR-CI roles and stable deployment roles;
- DEV personal/PR workspace permission boundaries;
- project CI/deployment WIF identity source;
- metadata/capture/checkpoint/quality/SCD primitives;
- deterministic offline SCD2 behavior oracle;
- reusable PR workspace and immutable project deployment workflows;
- query-tag/cost-attribution baseline.

This is not live Snowflake proof. Real remote state, account bootstrap/import, Terraform apply, WIF authentication, PR workspace execution, project deployment and live SCD2 execution are still pending.

Kafka Connector, direct Snowpipe Streaming and Openflow remain intentionally deferred until the live DEV foundation is proven.
