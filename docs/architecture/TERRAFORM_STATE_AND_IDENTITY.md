# Terraform State and Workload Identity

## Status

Phase 1 implementation baseline. Backend-independent source code, Azure Blob/S3 backend profiles, Snowflake workload identity code and static CI are present. A real remote-state control plane and Snowflake identity bootstrap still need to be configured/applied against actual accounts.

## Control-plane principle

Terraform state storage and Snowflake authentication are separate concerns:

```text
GitHub Actions
│
├── GitHub OIDC -> selected Terraform state backend
│                  ├── Azure Blob Storage (Microsoft-first reference)
│                  └── Amazon S3 (AWS reference)
│
└── GitHub OIDC -> Snowflake SERVICE user
                   └── AR_TERRAFORM_<ENV>
                       └── routine platform Terraform
```

Choosing Azure Blob or S3 for state does not change the Snowflake account/database/RBAC architecture.

## Why OneDrive / SharePoint is different

OneDrive and SharePoint are appropriate for shared human-facing material such as:

```text
architecture documents
runbooks
change records
audit evidence
approved reports
```

They are not the authoritative backend for live Terraform state. Terraform requires a backend contract with concurrency protection, consistency and machine access semantics. Do not store the collaborative `terraform.tfstate` in a synchronised OneDrive/SharePoint folder.

## Backend selection model

Terraform does not allow a backend type to be selected through an input variable. Each root therefore remains backend-free in committed source, and the selected backend declaration is materialised only at execution time:

```text
terraform/backend-profiles/azurerm/backend.tf
terraform/backend-profiles/s3/backend.tf
                │
                └── terraform/scripts/select-backend.sh
                            │
                            └── <root>/backend.generated.tf
```

`backend.generated.tf` is ignored by Git.

Supported values:

```text
TF_STATE_BACKEND=azurerm
TF_STATE_BACKEND=s3
```

An empty `TF_STATE_BACKEND` in the DEV plan workflow defaults to `azurerm` as the current Microsoft-first example.

## Azure Blob profile

The `azurerm` backend stores state as Azure Blob and uses Azure Blob native locking/consistency capabilities.

Reference authentication:

```text
GitHub OIDC
   -> Microsoft Entra workload federation
       -> Azure Blob container
```

Routine CI uses:

```text
ARM_USE_OIDC=true
ARM_USE_AZUREAD=true
AZURE_TENANT_ID / ARM_TENANT_ID
AZURE_CLIENT_ID / ARM_CLIENT_ID
TF_STATE_STORAGE_ACCOUNT
TF_STATE_CONTAINER
```

The baseline data-plane permission is `Storage Blob Data Contributor` scoped to the Terraform state container. Avoid client secrets for new CI workloads.

## Amazon S3 profile

The `s3` backend remains supported for AWS-centred organisations:

```text
GitHub OIDC
   -> AWS IAM role
       -> S3 state object + .tflock
```

Requirements:

- bucket versioning enabled;
- server-side encryption enabled;
- public access blocked;
- IAM limited to required state/lock prefixes;
- Terraform `use_lockfile = true`;
- no new DynamoDB locking dependency.

## State layout

The selected backend stores seven independent lifecycle states:

```text
enterprise-snowflake-platform-infra/organization/terraform.tfstate
enterprise-snowflake-platform-infra/identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/identity/uat/terraform.tfstate
enterprise-snowflake-platform-infra/identity/prod/terraform.tfstate
enterprise-snowflake-platform-infra/platform/dev/terraform.tfstate
enterprise-snowflake-platform-infra/platform/uat/terraform.tfstate
enterprise-snowflake-platform-infra/platform/prod/terraform.tfstate
```

A deployment chooses one authoritative backend for these states. Do not keep simultaneously writable S3 and Azure copies of the same state.

## GitHub Environments

Create GitHub Environments named:

```text
dev
uat
prod
```

Common Snowflake variables:

```text
SNOWFLAKE_ORGANIZATION_NAME
SNOWFLAKE_ACCOUNT_NAME
SNOWFLAKE_OIDC_AUDIENCE
```

Backend selector:

```text
TF_STATE_BACKEND=azurerm|s3
```

For Azure Blob:

```text
AZURE_TENANT_ID
AZURE_CLIENT_ID
TF_STATE_STORAGE_ACCOUNT
TF_STATE_CONTAINER
```

For S3:

```text
TF_STATE_BUCKET
TF_STATE_REGION
AWS_TERRAFORM_STATE_ROLE_ARN
```

`SNOWFLAKE_OIDC_AUDIENCE` remains independent of the state backend and must be scoped to the target Snowflake account.

## Snowflake identity bootstrap

Identity roots:

```text
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
```

Each creates:

```text
SU_GITHUB_TERRAFORM_<ENV>
AR_TERRAFORM_<ENV>
```

with GitHub OIDC trust and an account-scoped audience.

Initial identity bootstrap cannot authenticate using the identity it is about to create. Run it through a controlled administrator session against the target account with `ACCOUNTADMIN` activated only for the bootstrap operation.

## Routine Snowflake privileges

`AR_TERRAFORM_<ENV>` currently receives:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine execution does not activate ACCOUNTADMIN, SYSADMIN or SECURITYADMIN.

## GitHub OIDC subjects

```text
DEV  repo:ruizengalways/enterprise-snowflake-platform-infra:environment:dev
UAT  repo:ruizengalways/enterprise-snowflake-platform-infra:environment:uat
PROD repo:ruizengalways/enterprise-snowflake-platform-infra:environment:prod
```

## DEV plan workflow

`.github/workflows/terraform-plan-dev.yml` is manual-only.

It:

1. enters GitHub Environment `dev`;
2. resolves `TF_STATE_BACKEND` (default `azurerm`);
3. materialises the selected backend profile;
4. obtains/uses GitHub OIDC for Azure Blob or AWS S3 as applicable;
5. separately requests a GitHub OIDC token for Snowflake WIF;
6. initialises the DEV remote state key;
7. validates;
8. runs `terraform plan` only.

It intentionally does not apply and does not upload a reusable binary plan artifact.

## Promotion of infrastructure automation

```text
DEV identity + plan + apply + verification
       ↓
UAT identity + plan + apply + verification
       ↓
PROD identity + protected plan/apply
```

GitHub Environment approval rules remain part of the deployment control plane, especially for PROD.

## References

- ADR-022 — historical S3-only state choice; superseded.
- ADR-023 — GitHub OIDC workload identity for routine Terraform.
- ADR-024 — cloud-agnostic Azure Blob/S3 backend profiles.
- `docs/runbooks/terraform-platform-bootstrap.md`
- `docs/architecture/ACCOUNT_TOPOLOGY.md`
- `docs/architecture/RBAC_MODEL.md`
- `docs/standards/TERRAFORM_STANDARDS.md`
