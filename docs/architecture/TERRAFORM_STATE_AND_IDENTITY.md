# Terraform State and Workload Identity

## Status

Phase 1 source/static-CI baseline. Azure Blob/S3 backend profiles, platform Terraform WIF, DEV project-CI WIF source and the manual DEV plan path exist. No real remote state or Snowflake identity has been applied yet.

## Control-plane principle

Terraform state, platform Terraform identity and project delivery identity are separate concerns:

```text
GitHub Actions
│
├── OIDC -> selected Terraform state backend
│          ├── Azure Blob Storage
│          └── Amazon S3
│
├── OIDC -> SU_GITHUB_TERRAFORM_<ENV>
│          -> AR_TERRAFORM_<ENV>
│          -> platform Terraform
│
└── OIDC -> SU_GITHUB_<DOMAIN>_CI
           -> AR_<DOMAIN>_CI
           -> PR workspace lifecycle
```

Changing the state backend does not change Snowflake RBAC/domain design.

## OneDrive / SharePoint boundary

Use OneDrive/SharePoint for human-facing documents, runbooks, approvals, reports and audit evidence. Do not use a synchronised shared-drive file as authoritative live Terraform state.

## Backend selection

Terraform backend type is selected at execution time because backend type cannot be parameterised through a normal Terraform input variable:

```text
terraform/backend-profiles/azurerm/backend.tf
terraform/backend-profiles/s3/backend.tf
          -> terraform/scripts/select-backend.sh
          -> <root>/backend.generated.tf   # ignored
```

Supported values:

```text
TF_STATE_BACKEND=azurerm
TF_STATE_BACKEND=s3
```

Azure Blob is the Microsoft-first reference. S3 remains a supported AWS reference.

## State layout

There are now eight lifecycle state objects:

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

Why the extra DEV project-identity state:

```text
identity/dev
  creates platform Terraform identity
        ↓
platform/dev
  creates AR_<DOMAIN>_CI roles
        ↓
project-identity/dev
  creates project CI service users bound to those existing roles
```

Combining these would either create a dependency cycle or let routine platform state own a delivery identity it should not control.

A deployment chooses one authoritative backend. Do not keep Azure Blob and S3 simultaneously writable for the same state.

## Azure Blob profile

Reference authentication:

```text
GitHub OIDC -> Microsoft Entra workload federation -> Azure Blob container
```

Baseline variables:

```text
ARM_USE_OIDC=true
ARM_USE_AZUREAD=true
AZURE_TENANT_ID / ARM_TENANT_ID
AZURE_CLIENT_ID / ARM_CLIENT_ID
TF_STATE_STORAGE_ACCOUNT
TF_STATE_CONTAINER
```

Baseline data-plane access is `Storage Blob Data Contributor` scoped to the state container. Avoid client secrets for new automation.

## Amazon S3 profile

```text
GitHub OIDC -> AWS IAM role -> S3 state + .tflock
```

Require bucket versioning, encryption, public-access blocking, prefix-scoped IAM and Terraform native `use_lockfile = true`. Do not introduce deprecated DynamoDB locking for new deployments.

## Platform Terraform identity

Roots:

```text
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
```

Create:

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Routine privileges:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine Terraform does not activate ACCOUNTADMIN, SYSADMIN or SECURITYADMIN. Identity bootstrap may use ACCOUNTADMIN only to establish machine identity/WIF.

Platform OIDC subjects:

```text
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:dev
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:uat
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:prod
```

## DEV project-CI identities

Root:

```text
terraform/stacks/project-identity/dev/
```

Generic module:

```text
terraform/modules/service-identity/
```

Current identities:

```text
SU_GITHUB_HEALTH_CI
  -> AR_HEALTH_CI
  -> subject repo:ruizengalways/enterprise-snowflake-health-analytics:environment:ci

SU_GITHUB_TRANSPORT_CI
  -> AR_TRANSPORT_CI
  -> subject repo:ruizengalways/enterprise-snowflake-transport-analytics:environment:ci
```

The module creates only the SERVICE user/WIF trust and grants an existing role. It does not create account-level privileges.

`project-identity/dev` must execute after `platform/dev` because the CI roles are owned by the platform state.

See ADR-027.

## Account-scoped OIDC audience

Platform and project identities require a non-empty account-scoped Snowflake OIDC audience. The shared `snowflakecomputing.com` audience is rejected by the Terraform modules.

The Snowflake first-party GitHub action currently configures `snowflakecomputing.com` automatically when `use-oidc: true`; therefore the reusable project PR workflow installs the action/CLI with `use-oidc: false`, explicitly requests a GitHub token with the configured account-scoped audience, and exports that short-lived token to Snowflake CLI.

This preserves the account-scoped audience security boundary without storing a password/private key.

## GitHub Environments

Platform Infra repository:

```text
dev
uat
prod
```

Health and Transport project repositories:

```text
ci
```

Project `ci` environment must eventually define:

```text
SNOWFLAKE_ACCOUNT
SNOWFLAKE_OIDC_AUDIENCE
```

The Snowflake service user, role, warehouse and database are convention-derived from the domain code by the reusable workflow.

## DEV platform plan

`.github/workflows/terraform-plan-dev.yml` remains manual-only, backend-selectable and plan-only.

## PR workspace workflow

Framework:

```text
enterprise-snowflake-data-project-framework/.github/workflows/pr-workspace.yml
```

Thin project callers are pinned to a framework commit. The reusable workflow:

1. targets GitHub Environment `ci`;
2. validates the domain/action inputs;
3. renders framework-owned QUERY_TAG/workspace SQL;
4. installs a pinned Snowflake Action + Snowflake CLI;
5. requests a custom-audience GitHub OIDC token;
6. connects as `SU_GITHUB_<DOMAIN>_CI` with `AR_<DOMAIN>_CI`;
7. executes only the generated local workspace SQL;
8. creates on PR open/reopen/synchronize and drops on PR close.

It does not yet execute untrusted project PR business code under Snowflake credentials.

## Real execution order

```text
remote state control plane
-> organization bootstrap/import
-> identity/dev
-> platform/dev plan/apply/verify
-> project-identity/dev
-> configure Health/Transport GitHub Environment ci
-> real PR workspace create/drop test
-> UAT
-> PROD
```

## References

- ADR-023 — platform Terraform GitHub OIDC identity.
- ADR-024 — Azure Blob/S3 backend adapters.
- ADR-025 — DEV personal and PR CI workspace lifecycle.
- ADR-027 — project PR-CI OIDC identity lifecycle.
- `docs/CURRENT_CONTEXT.md`
- `docs/runbooks/terraform-platform-bootstrap.md`
