# Terraform Platform Foundation

Terraform owns selected stable Snowflake platform infrastructure.

## Layout

```text
terraform/
├── backend-profiles/
│   ├── azurerm/backend.tf
│   └── s3/backend.tf
├── scripts/
│   └── select-backend.sh
├── modules/
│   ├── analytics-environment/
│   ├── warehouse/
│   ├── platform-control/
│   ├── rbac/
│   └── workload-identity/
└── stacks/
    ├── organization/
    ├── identity/{dev,uat,prod}/
    ├── dev/
    ├── uat/
    └── prod/
```

Every root commits its own `.terraform.lock.hcl`. CI uses `terraform init -lockfile=readonly` so dependency drift cannot be silently accepted.

## Versions

```text
Terraform CLI:                1.16.0
Snowflake provider:           2.19.0
Provider source:              snowflakedb/snowflake
```

## Bootstrap boundaries

### Organization

`terraform/stacks/organization` is the only root that uses ORGADMIN. It creates or imports DEV/UAT/PROD Snowflake accounts. Account resources use `prevent_destroy = true`.

### Workload identity

`terraform/stacks/identity/{dev,uat,prod}` bootstrap:

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Identity bootstrap is separate because routine automation must not own the state capable of destroying its own authentication path.

## Routine provider authority

Routine DEV/UAT/PROD roots expose:

```text
snowflake.objects
snowflake.security
```

Both aliases activate `AR_TERRAFORM_<ENV>` rather than Snowflake system roles.

Initial account-level privileges are:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

The role is machine-only.

## Remote state backend adapters

The Snowflake roots do not commit a backend type. Terraform permits only one backend block per root and backend type cannot be selected through Terraform input variables, so the execution layer materialises the selected profile:

```bash
bash terraform/scripts/select-backend.sh azurerm terraform/stacks/dev
# or
bash terraform/scripts/select-backend.sh s3 terraform/stacks/dev
```

This writes an ignored:

```text
terraform/stacks/dev/backend.generated.tf
```

### Azure Blob profile — Microsoft-first reference

`terraform/backend-profiles/azurerm/backend.tf` uses Terraform's `azurerm` backend.

Reference CI authentication:

```text
GitHub OIDC
  -> Microsoft Entra workload federation
      -> Azure Blob Storage container
```

Required deployment metadata includes:

```text
AZURE_TENANT_ID
AZURE_CLIENT_ID
TF_STATE_STORAGE_ACCOUNT
TF_STATE_CONTAINER
```

Routine CI sets `ARM_USE_OIDC=true` and `ARM_USE_AZUREAD=true`. The baseline Azure data-plane role is `Storage Blob Data Contributor` scoped to the state container.

Azure Blob provides native Terraform state locking/consistency behavior; no separate lock database is required.

### Amazon S3 profile — AWS reference

`terraform/backend-profiles/s3/backend.tf` retains:

```hcl
terraform {
  backend "s3" {
    encrypt      = true
    use_lockfile = true
  }
}
```

Reference CI authentication is GitHub OIDC -> AWS IAM role. The bucket must use versioning, encryption, public-access blocking and tightly scoped state/`.tflock` permissions. New deployments do not use deprecated DynamoDB locking.

### OneDrive / SharePoint

Use OneDrive/SharePoint for human-facing documents, runbooks, approvals and audit evidence if that matches the enterprise collaboration stack. Do **not** use a synchronised OneDrive/SharePoint folder as the authoritative live `terraform.tfstate` backend.

### State boundaries

Whichever backend is selected, preserve these seven independent keys:

```text
enterprise-snowflake-platform-infra/organization/terraform.tfstate
enterprise-snowflake-platform-infra/identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/identity/uat/terraform.tfstate
enterprise-snowflake-platform-infra/identity/prod/terraform.tfstate
enterprise-snowflake-platform-infra/platform/dev/terraform.tfstate
enterprise-snowflake-platform-infra/platform/uat/terraform.tfstate
enterprise-snowflake-platform-infra/platform/prod/terraform.tfstate
```

One deployment has one writable source of truth for a state. Do not actively mirror the same state to Azure Blob and S3 as two writable backends.

See ADR-024 and `docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`.

## Domain model

```text
DEV account
├── DEV_HEALTH
├── CI_HEALTH
├── DEV_TRANSPORT
└── CI_TRANSPORT

UAT account
├── UAT_HEALTH
└── UAT_TRANSPORT

PROD account
├── PROD_HEALTH
└── PROD_TRANSPORT
```

Every account also has `PLATFORM_CONTROL`.

Every domain receives:

```text
AR_<DOMAIN>_GUEST -> READER -> DEVELOPER -> ADMIN
DR_<DOMAIN>_ANALYTICS_GUEST -> READ -> WRITE -> OWNER
```

Warehouses:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
```

Employee membership is not Terraform-managed; the enterprise IdP/SCIM layer assigns people to the account roles defined by Terraform.

## Static validation baseline

GitHub Actions validates:

```text
organization
identity/dev
identity/uat
identity/prod
dev
uat
prod
```

with:

```text
terraform fmt -check -recursive terraform
terraform init -backend=false -input=false -lockfile=readonly
terraform validate -no-color
```

CI also materialises and validates both `azurerm` and `s3` backend profiles without connecting to either cloud.

Static validation does not prove real cloud backend access or real Snowflake privileges.

## DEV remote-plan spine

`.github/workflows/terraform-plan-dev.yml` is manual-only and has no apply step.

It accepts:

```text
TF_STATE_BACKEND=azurerm|s3
```

Empty currently defaults to `azurerm` as the Microsoft-first reference path.

Common Snowflake inputs:

```text
SNOWFLAKE_ORGANIZATION_NAME
SNOWFLAKE_ACCOUNT_NAME
SNOWFLAKE_OIDC_AUDIENCE
```

Azure state inputs:

```text
AZURE_TENANT_ID
AZURE_CLIENT_ID
TF_STATE_STORAGE_ACCOUNT
TF_STATE_CONTAINER
```

S3 state inputs:

```text
TF_STATE_BUCKET
TF_STATE_REGION
AWS_TERRAFORM_STATE_ROLE_ARN
```

The Snowflake WIF path is identical regardless of state backend.

## Apply policy

No automated apply is enabled yet. Progression is:

```text
selected remote-state control plane
        ↓
organization account bootstrap/import
        ↓
DEV identity bootstrap
        ↓
DEV remote plan
        ↓
reviewed DEV apply + Snowflake verification
        ↓
UAT identity/plan/apply + verification
        ↓
protected PROD identity/plan/apply
```

Do not widen `AR_TERRAFORM_DEV` pre-emptively; use the first real DEV plan/apply to identify any demonstrated privilege gaps.
