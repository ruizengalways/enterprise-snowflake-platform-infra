# Terraform Standards

## Scope

These standards apply to `enterprise-snowflake-platform-infra`.

## Versions and dependency locks

```text
Terraform CLI                 1.16.0
Snowflake Terraform provider  2.19.0
```

- Every root pins Terraform/provider versions.
- Every root commits `.terraform.lock.hcl`.
- CI uses `terraform init -lockfile=readonly`.
- Provider upgrades require migration-guide review and CI validation.

## Credential rule

Never commit passwords, private keys, OAuth/OIDC tokens, cloud access keys, PATs, Terraform state or real secret-bearing tfvars.

## Terraform lifecycle roots

Current roots:

```text
terraform/stacks/organization/
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
terraform/stacks/dev/
terraform/stacks/project-identity/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

They represent eight independent state/lifecycle boundaries.

### Organization root

- the only root using ORGADMIN;
- creates/imports DEV/UAT/PROD account resources;
- account resources use `prevent_destroy`.

### Platform identity roots

`identity/<env>` may use ACCOUNTADMIN only to bootstrap:

```text
SU_GITHUB_TERRAFORM_<ENV>
AR_TERRAFORM_<ENV>
GitHub OIDC WIF trust
```

Routine account Terraform must never own the identity it uses to authenticate.

### Routine account roots

`dev/uat/prod` use provider aliases:

```text
snowflake.objects
snowflake.security
```

Both activate:

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

Do not fall back to ACCOUNTADMIN/SYSADMIN/SECURITYADMIN for routine CI. Add privileges only when a live plan/apply demonstrates a specific requirement.

### Project identity root

`project-identity/dev` executes only **after** `platform/dev` because it binds service users to CI roles created by platform state.

It creates:

```text
SU_GITHUB_<DOMAIN>_CI -> existing AR_<DOMAIN>_CI
```

using the generic `service-identity` module.

It must not create/expand project CI roles or receive account-level privileges. UAT/PROD deployment identities are future separate lifecycles; do not reuse DEV CI identities.

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

Prefer GitHub OIDC -> Microsoft Entra workload federation. Baseline data-plane permission is `Storage Blob Data Contributor` scoped to the state container. Avoid client secrets.

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
enterprise-snowflake-platform-infra/project-identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/platform/uat/terraform.tfstate
enterprise-snowflake-platform-infra/platform/prod/terraform.tfstate
```

Never keep Azure Blob and S3 simultaneously writable for the same state.

## OIDC standards

Use repository + GitHub Environment scoped subjects.

Platform:

```text
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:dev
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:uat
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:prod
```

Project CI:

```text
repo:ruizengalways/enterprise-snowflake-health-analytics:environment:ci
repo:ruizengalways/enterprise-snowflake-transport-analytics:environment:ci
```

Use a non-empty **account-scoped** Snowflake OIDC audience. Do not use `snowflakecomputing.com` for these identities.

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

- `analytics-environment` owns stable domain DB/schema structure;
- `rbac` owns stable human domain/platform roles and grants;
- `workspace-access` owns DEV `CREATE SCHEMA` + machine CI role/database-role/warehouse boundary;
- `workload-identity` creates a platform Terraform role plus service identity;
- `service-identity` binds a WIF service user to an already-existing role;
- do not create wrapper modules that hide a single line or real business differences.

A database has one owning domain; never recreate a domain × database Cartesian product.

## Employee boundary

Terraform defines the RBAC model, not employee membership.

```text
Entra / Okta group
  -> SCIM / approved provisioning
      -> AR_<DOMAIN>_<CAPABILITY>
```

Employee joins/leaves must not create routine Terraform changes.

## Human and CI database boundary

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
```

Do not attach human GUEST/READER/DEVELOPER/ADMIN roles to CI databases.

## Resource ownership

Terraform owns selected stable infrastructure/RBAC/identity boundaries. It does not own dbt business models, employee records, individual PR schemas or routine data changes.

One object has one authoritative lifecycle owner.

## Validation

Every Terraform change must pass:

```text
terraform fmt -check -recursive
terraform init -backend=false -input=false -lockfile=readonly
terraform validate
```

Current CI validates all eight roots plus both backend declarations.

Static validation proves provider/HCL correctness, not live Snowflake authorization.

## Apply order

```text
remote state
-> organization
-> identity/dev
-> platform/dev
-> project-identity/dev
-> project PR workspace live test
-> UAT
-> PROD
```

No automated apply is enabled yet.
