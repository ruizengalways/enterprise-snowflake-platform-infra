# RBAC Model

## Status

Phase 1 executable baseline. Domain human roles, published-data GUEST access, DEV personal workspace permission, machine-only PR CI roles, machine-only project deployment roles, domain warehouses, and per-account Terraform/deployment identities are implemented in Terraform source/static CI. Real Snowflake apply/effective-privilege verification is still pending.

## Principles

1. Account roles describe human or machine capability inside one Snowflake account.
2. Database roles encapsulate object/database access inside one governed domain database.
3. Every analytics database belongs to exactly one domain/data product.
4. Human and machine roles are separate.
5. `GUEST` is authenticated published-data read-only access, not Snowflake `PUBLIC`.
6. UAT/PROD human developers are read-only by default.
7. `CI_<DOMAIN>` is machine-only; human domain roles do not attach to CI databases.
8. Routine UAT/PROD transform compute is machine-only through `AR_<DOMAIN>_DEPLOY`.
9. Terraform manages role/privilege models, not day-to-day employee membership.
10. Stable Terraform-owned schemas retain platform lifecycle ownership.

## Platform human roles

```text
AR_PLATFORM_READER
  -> AR_PLATFORM_ENGINEER
  -> AR_PLATFORM_ADMIN
  -> SYSADMIN
```

Platform authority does not automatically imply Health/Transport domain authority.

## Domain human roles

Each domain has an independent hierarchy:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
  -> SYSADMIN
```

Examples:

```text
AR_HEALTH_GUEST / READER / DEVELOPER / ADMIN
AR_TRANSPORT_GUEST / READER / DEVELOPER / ADMIN
```

A person may hold roles in multiple domains, but Health authority never implies Transport authority.

`ADMIN` remains a governed human administration role. In UAT/PROD it does **not** receive permanent transform-warehouse `USAGE` from the baseline. Emergency execution must be granted just-in-time through the enterprise identity-governance/break-glass process and removed afterwards; individual emergency grants are not encoded in Terraform.

## Stable domain database roles

Human roles attach only to stable environment databases such as `DEV_HEALTH`, `UAT_HEALTH`, and `PROD_HEALTH`:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
  -> DR_<DOMAIN>_ANALYTICS_READ
  -> DR_<DOMAIN>_ANALYTICS_WRITE
  -> DR_<DOMAIN>_ANALYTICS_OWNER
```

### GUEST

Receives:

- database `USAGE`;
- schema `USAGE` only on configured published schemas;
- `SELECT` on current/future tables, views and semantic views in those published schemas.

Initial published schemas:

```text
MARTS
SEMANTIC
```

GUEST does not receive STAGING/INTERMEDIATE/CANONICAL/RAW, DDL, transform compute, or CI database access.

### READ

Inherits GUEST and can inspect all stable domain schemas through schema `USAGE` and current/future `SELECT` grants.

### WRITE

Inherits READ and adds ordinary dbt-development schema DDL:

```text
CREATE TABLE
CREATE VIEW
CREATE STAGE
CREATE FILE FORMAT
CREATE SEQUENCE
```

In the DEV account only, the WRITE database role also receives `CREATE SCHEMA` on the matching `DEV_<DOMAIN>` database so developers can create personal workspaces.

Personal schema convention:

```text
<DEVELOPER>_<LAYER>
```

This is a namespace convention, not a per-person security boundary: developers share the domain developer role. Stronger individual isolation would require identity-governed personal roles.

### OWNER

Inherits WRITE and is the domain's highest governed database-access tier for `AR_<DOMAIN>_ADMIN`. The name does not imply automatic transfer of Terraform-managed database/schema object ownership.

## PR CI machine roles

DEV creates separate machine capabilities:

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> USAGE + CREATE SCHEMA on CI_<DOMAIN>
  -> USAGE on WH_<DOMAIN>_CI
  -> EXECUTE TASK
```

Current examples:

```text
AR_HEALTH_CI
CI_HEALTH.DR_HEALTH_CI_WORKSPACE
WH_HEALTH_CI

AR_TRANSPORT_CI
CI_TRANSPORT.DR_TRANSPORT_CI_WORKSPACE
WH_TRANSPORT_CI
```

These roles are not in the human GUEST -> READER -> DEVELOPER -> ADMIN hierarchy. Human domain roles do not attach to CI databases. A project-specific GitHub OIDC service identity receives the matching `AR_<DOMAIN>_CI` role.

PR schemas follow:

```text
PR_<NUMBER>_<LAYER>
```

The shared framework renders guarded create/drop SQL. Because the CI role creates the PR schema, schema ownership supplies object-creation authority inside that ephemeral workspace; the account-level `EXECUTE TASK` grant supports warehouse-backed task execution without granting serverless `EXECUTE MANAGED TASK`.

## Project deployment machine roles

Stable DEV/UAT/PROD deployment uses a dedicated machine role per domain:

```text
SU_GITHUB_<DOMAIN>_DEPLOY
  -> AR_<DOMAIN>_DEPLOY
      -> DR_<DOMAIN>_ANALYTICS_WRITE
      -> USAGE on WH_<DOMAIN>_TRANSFORM
      -> CREATE STREAM on stable domain schemas
      -> CREATE TASK on stable domain schemas
      -> CREATE DYNAMIC TABLE on stable domain schemas
      -> EXECUTE TASK
```

`AR_<DOMAIN>_DEPLOY` is intentionally outside the human role hierarchy. The deployment role owns long-lived Snowflake-native runtime objects created by project delivery so Tasks and Dynamic Tables do not depend on a human role retaining background-runtime privileges.

Deployment identities use GitHub OIDC / Snowflake Workload Identity Federation; no password or private key is committed. GitHub deployment workflows are pinned by immutable framework SHA and deploy an explicit full project Git SHA.

## Warehouse isolation

Each domain owns:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
```

Human baseline grants:

```text
GUEST         -> QUERY
READER        -> inherited QUERY
DEV DEVELOPER -> TRANSFORM
UAT/PROD human roles -> no permanent TRANSFORM grant
```

Machine grants:

```text
AR_<DOMAIN>_CI     -> WH_<DOMAIN>_CI      # DEV only
AR_<DOMAIN>_DEPLOY -> WH_<DOMAIN>_TRANSFORM
```

Human UAT/PROD emergency transform execution is a JIT identity-governance action, not a standing Terraform grant.

Environment project metadata identifies the query/transform/CI warehouse keys, so adding a new domain does not require hard-coded Health/Transport role-grant blocks in root Terraform.

## Employee identity

Terraform defines which roles exist and what they can access. Entra ID / Okta / SCIM or another approved identity-governance path controls who receives them.

Target pattern:

```text
Employee -> IdP group -> SCIM/approved provisioning -> AR_<DOMAIN>_<CAPABILITY>
```

Adding/removing an employee from an existing domain should not require editing Terraform.

Break-glass/JIT access follows the same boundary: identity governance temporarily grants an approved human capability or emergency compute entitlement; Terraform does not add a named employee or permanent UAT/PROD transform grant.

## Terraform machine identities

Platform Terraform has a separate service user/role per account:

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Initial routine privileges:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine account roots do not activate ACCOUNTADMIN, SYSADMIN or SECURITYADMIN. Identity bootstrap is the exceptional lifecycle that may use ACCOUNTADMIN to create the dedicated service user/role/WIF trust.

Project workload identities are bootstrapped separately after the environment platform stack has created their target machine roles:

```text
project-identity/dev  -> SU_GITHUB_<DOMAIN>_CI and SU_GITHUB_<DOMAIN>_DEPLOY
project-identity/uat  -> SU_GITHUB_<DOMAIN>_DEPLOY
project-identity/prod -> SU_GITHUB_<DOMAIN>_DEPLOY
```

## GitHub OIDC trust

Platform Terraform subjects are repository + GitHub Environment scoped:

```text
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:dev
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:uat
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:prod
```

Project workload subjects are also repository + GitHub Environment scoped, but bind to the individual analytics repository so a Health workflow cannot authenticate as a Transport deployment identity.

Each account uses an account-scoped OIDC audience rather than the shared `snowflakecomputing.com` audience.

## Environment summary

```text
DEV
  humans: GUEST/READER/DEVELOPER/ADMIN on DEV_<DOMAIN>
  developer: WRITE + CREATE SCHEMA + TRANSFORM
  machines: AR_<DOMAIN>_CI on CI_<DOMAIN> + WH_<DOMAIN>_CI
            AR_<DOMAIN>_DEPLOY on DEV_<DOMAIN> + WH_<DOMAIN>_TRANSFORM

UAT
  humans: GUEST/READER/DEVELOPER(read-only)/ADMIN
  machines: AR_<DOMAIN>_DEPLOY on UAT_<DOMAIN> + WH_<DOMAIN>_TRANSFORM
  emergency human transform: JIT/break-glass only

PROD
  humans: GUEST/READER/DEVELOPER(read-only)/ADMIN
  machines: AR_<DOMAIN>_DEPLOY on PROD_<DOMAIN> + WH_<DOMAIN>_TRANSFORM
  emergency human transform: JIT/break-glass only
```

## Verification gate

Static Terraform CI validates provider/resource schemas but not live authorization. The first DEV plan/apply must prove these grants and role relationships in a real Snowflake account before UAT/PROD rollout. Live verification must also prove the deployment service identity can create/own warehouse-backed Streams, Tasks and Dynamic Tables without a human ADMIN transform grant.

See ADR-020, ADR-023, ADR-025 and `TERRAFORM_STATE_AND_IDENTITY.md`.
