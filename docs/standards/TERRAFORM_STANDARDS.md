# Terraform Standards

## Scope

These standards apply to `enterprise-snowflake-platform-infra`.

## Versions and dependency locks

```text
Terraform CLI                 1.16.0
Snowflake Terraform provider  2.19.0
```

- Every Terraform root pins Terraform/provider versions.
- Every root commits `.terraform.lock.hcl`.
- CI uses `terraform init -backend=false -input=false -lockfile=readonly` for static validation.
- Provider upgrades require migration-guide review and full static CI validation before live plans.

## Credential rule

Never commit passwords, private keys, OAuth/OIDC tokens, cloud access keys, PATs, Terraform state or secret-bearing real tfvars.

## Terraform lifecycle roots

Current roots:

```text
terraform/stacks/organization/
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
terraform/stacks/project-identity/dev/
terraform/stacks/project-identity/uat/
terraform/stacks/project-identity/prod/
```

They represent ten independent state/lifecycle boundaries.

### Organization root

- the only root using ORGADMIN;
- creates/imports DEV/UAT/PROD account resources;
- account lifecycle receives destructive-change protection;
- never run routine account infrastructure through this root.

### Platform identity roots

`identity/<env>` may use ACCOUNTADMIN only to bootstrap:

```text
SU_GITHUB_TERRAFORM_<ENV>
AR_TERRAFORM_<ENV>
GitHub OIDC WIF trust
```

Routine account Terraform must never own the identity it uses to authenticate.

### Routine account roots

`dev/uat/prod` activate only:

```text
AR_TERRAFORM_<ENV>
```

Initial account-level privileges:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Do not fall back to ACCOUNTADMIN/SYSADMIN/SECURITYADMIN for routine CI. Add privileges only when a live plan/apply demonstrates a specific missing requirement.

Routine roots own stable domain databases/schemas, warehouses, role models, grants and structural `PLATFORM_CONTROL` boundaries.

### Project identity roots

`project-identity/<env>` executes only **after** `platform/<env>` because it binds service users to machine roles created by platform state.

DEV creates:

```text
SU_GITHUB_<DOMAIN>_CI     -> existing AR_<DOMAIN>_CI
SU_GITHUB_<DOMAIN>_DEPLOY -> existing AR_<DOMAIN>_DEPLOY
```

UAT/PROD create:

```text
SU_GITHUB_<DOMAIN>_DEPLOY -> existing AR_<DOMAIN>_DEPLOY
```

The generic `service-identity` module owns only SERVICE user/WIF trust + role assignment. It must not create/expand the target role or grant account-level privileges.

## State backend adapters

The platform is backend-agnostic:

```text
azurerm -> Azure Blob Storage
s3      -> Amazon S3
```

Terraform backend type is selected before init:

```bash
bash terraform/scripts/select-backend.sh <azurerm|s3> terraform/stacks/<root>
```

This writes ignored `backend.generated.tf` from `terraform/backend-profiles/`.

### Azure Blob

Prefer GitHub OIDC -> Microsoft Entra workload federation. Baseline data-plane permission is `Storage Blob Data Contributor` scoped to the state container. Avoid client secrets for new automation.

### S3

Use GitHub OIDC -> AWS IAM, bucket versioning/encryption/public-access blocking, prefix-scoped permissions and Terraform native `use_lockfile = true`. Do not add deprecated DynamoDB locking to new deployments.

### OneDrive / SharePoint

Valid for documents/runbooks/approvals/audit evidence, not authoritative live Terraform state.

## State objects

```text
enterprise-snowflake-platform-infra/organization/terraform.tfstate
enterprise-snowflake-platform-infra/identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/identity/uat/terraform.tfstate
enterprise-snowflake-platform-infra/identity/prod/terraform.tfstate
enterprise-snowflake-platform-infra/platform/dev/terraform.tfstate
enterprise-snowflake-platform-infra/platform/uat/terraform.tfstate
enterprise-snowflake-platform-infra/platform/prod/terraform.tfstate
enterprise-snowflake-platform-infra/project-identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/project-identity/uat/terraform.tfstate
enterprise-snowflake-platform-infra/project-identity/prod/terraform.tfstate
```

Never keep Azure Blob and S3 simultaneously writable for the same state.

## OIDC standards

Use repository + GitHub Environment scoped subjects.

Platform Terraform:

```text
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:dev
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:uat
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:prod
```

Project PR CI:

```text
repo:ruizengalways/enterprise-snowflake-health-analytics:environment:ci
repo:ruizengalways/enterprise-snowflake-transport-analytics:environment:ci
```

Project stable deployment follows the same repository boundary with target environments `dev`, `uat`, `prod`.

Use a non-empty account-scoped Snowflake OIDC audience. Do not use the shared `snowflakecomputing.com` audience for these workload identities.

Snowflake provider experiment `USER_ENABLE_DEFAULT_WORKLOAD_IDENTITY` is limited to roots that manage service-user WIF configuration.

## Modules

Current modules:

```text
analytics-environment
warehouse
platform-control
rbac
workspace-access
workload-identity
service-identity
```

Rules:

- `analytics-environment` owns stable domain database/schema structure;
- `rbac` owns stable human, CI and deployment role/grant models;
- `workspace-access` owns DEV `CREATE SCHEMA` + machine CI role/database-role/warehouse boundary;
- `workload-identity` creates a platform Terraform role plus service identity;
- `service-identity` binds a WIF service user to an already-existing role;
- do not create wrapper modules that hide a single line or genuinely different business/source behavior.

A database has one owning domain; never recreate a domain × database Cartesian product.

## Employee boundary

Terraform defines the RBAC model, not employee membership.

```text
Entra / Okta group
  -> SCIM / approved provisioning
  -> AR_<DOMAIN>_<CAPABILITY>
```

Employee joins/leaves must not create routine Terraform changes.

Emergency UAT/PROD transform access is also an identity-governance/JIT event, not a permanent Terraform grant to named employees.

## Human, CI and deployment boundaries

Human domain roles attach to stable environment databases only.

DEV personal workspace capability:

```text
DR_<DOMAIN>_ANALYTICS_WRITE
  -> CREATE SCHEMA on DEV_<DOMAIN>
```

Machine PR CI:

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
  -> CREATE SCHEMA on CI_<DOMAIN>
  -> WH_<DOMAIN>_CI
  -> EXECUTE TASK
```

Stable project deployment:

```text
AR_<DOMAIN>_DEPLOY
  -> DR_<DOMAIN>_ANALYTICS_WRITE
  -> WH_<DOMAIN>_TRANSFORM
  -> CREATE STREAM/TASK/DYNAMIC TABLE on stable domain schemas
  -> EXECUTE TASK
```

Do not grant `EXECUTE MANAGED TASK` while the baseline uses named warehouses.

Do not attach human GUEST/READER/DEVELOPER/ADMIN roles to CI databases. Do not grant permanent UAT/PROD transform compute to human roles in the baseline.

## Resource ownership

Terraform owns selected stable infrastructure/RBAC/identity boundaries. It does not own dbt business models, employee records, individual PR schemas or routine data changes.

Terraform creates the structural `PLATFORM_CONTROL` database/schemas; native platform SQL owns operational tables/procedures inside that boundary. Do not use `null_resource`/`local-exec` to make Terraform own those SQL objects.

One object has one authoritative lifecycle owner.

## Validation

Every Terraform change must pass:

```text
terraform fmt -check -recursive
terraform init -backend=false -input=false -lockfile=readonly
terraform validate
```

Current static CI validates all ten roots plus both backend declarations:

```text
organization
identity/dev
identity/uat
identity/prod
dev
uat
prod
project-identity/dev
project-identity/uat
project-identity/prod
backend azurerm
backend s3
```

Static validation proves HCL/provider-schema correctness, not live Snowflake authorization.

## Apply order

```text
remote state control plane
-> organization bootstrap/import

DEV:
identity/dev
-> platform/dev reviewed plan/apply/verify
-> project-identity/dev
-> project PR workspace + stable deployment live tests

UAT:
identity/uat
-> platform/uat reviewed plan/apply/verify
-> project-identity/uat
-> immutable promotion test

PROD:
identity/prod
-> platform/prod protected plan/apply/verify
-> project-identity/prod
-> exact approved SHA promotion
```

No automated Terraform apply is enabled yet. Do not automate apply before live DEV remote-state/WIF/least-privilege behavior is understood.

See ADR-023, ADR-024, ADR-027 and ADR-034.
