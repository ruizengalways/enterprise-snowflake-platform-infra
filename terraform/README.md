# Terraform Platform Foundation

Terraform owns selected stable Snowflake platform infrastructure.

## Layout

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

Every root commits `.terraform.lock.hcl`; CI uses `-lockfile=readonly`.

## Versions

```text
Terraform CLI:       1.16.0
Snowflake provider:  2.19.0
```

## Privileged lifecycle boundaries

`organization/` alone uses ORGADMIN for DEV/UAT/PROD account lifecycle.

`identity/{dev,uat,prod}` bootstraps platform Terraform service users/roles:

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Routine `dev/uat/prod` roots activate only `AR_TERRAFORM_<ENV>` through the `snowflake.objects` and `snowflake.security` aliases.

Initial routine privileges:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

## Domain infrastructure

Stable databases:

```text
DEV_<DOMAIN>
UAT_<DOMAIN>
PROD_<DOMAIN>
```

DEV also contains:

```text
CI_<DOMAIN>
```

Human domain roles:

```text
AR_<DOMAIN>_GUEST -> READER -> DEVELOPER -> ADMIN
```

Stable database roles:

```text
DR_<DOMAIN>_ANALYTICS_GUEST -> READ -> WRITE -> OWNER
```

Warehouses:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
```

Environment project metadata now declares the query/transform/CI warehouse keys. Root stacks derive grants from metadata instead of hard-coding Health/Transport role/warehouse pairs.

## DEV workspace access

The DEV root deliberately separates human workspaces from PR CI.

### Human DEV

Human domain RBAC attaches only to `DEV_<DOMAIN>` databases, not `CI_<DOMAIN>`.

The DEV domain WRITE database role receives `CREATE SCHEMA` on the matching `DEV_<DOMAIN>` database. This allows personal workspace names such as:

```text
ALICE_STAGING
ALICE_MARTS
```

Personal schema prefixes are workspace conventions, not security boundaries between people sharing `AR_<DOMAIN>_DEVELOPER`.

### PR CI

`workspace-access` creates a machine-only capability per domain:

```text
AR_<DOMAIN>_CI
  -> CI_<DOMAIN>.DR_<DOMAIN>_CI_WORKSPACE
      -> USAGE + CREATE SCHEMA on CI_<DOMAIN>
  -> USAGE on WH_<DOMAIN>_CI
```

Human GUEST/READER/DEVELOPER/ADMIN roles do not attach to CI databases.

The framework repo owns guarded rendering of `PR_<NUMBER>_<LAYER>` create/drop SQL. A later project-CI OIDC service identity will receive `AR_<DOMAIN>_CI`.

See ADR-025.

## Remote state backend adapters

The Snowflake roots do not commit one cloud-specific backend. Runtime materialises one profile:

```bash
bash terraform/scripts/select-backend.sh azurerm terraform/stacks/dev
# or
bash terraform/scripts/select-backend.sh s3 terraform/stacks/dev
```

This writes ignored `backend.generated.tf`.

### Azure Blob — Microsoft-first reference

```text
GitHub OIDC -> Microsoft Entra workload federation -> Azure Blob
```

Use `Storage Blob Data Contributor` scoped to the state container as the baseline data-plane access.

### Amazon S3 — AWS alternative

```text
GitHub OIDC -> AWS IAM -> S3 + .tflock
```

Use versioning, encryption, blocked public access and Terraform native `use_lockfile = true`; do not introduce deprecated DynamoDB locking for new deployments.

OneDrive/SharePoint may hold human-facing docs/evidence, not the authoritative live Terraform state.

Whichever backend is selected, retain seven independent state keys for organization, three identity roots and three routine account roots.

## Static validation

Platform Infra CI validates:

```text
terraform fmt
organization
identity/dev
identity/uat
identity/prod
dev
uat
prod
backend azurerm
backend s3
```

The DEV workspace-access slice has passed Terraform provider `2.19.0` init/validate in CI.

Static validation does not prove live Snowflake authorization or remote backend connectivity.

## DEV remote plan

`.github/workflows/terraform-plan-dev.yml` remains manual-only and supports `TF_STATE_BACKEND=azurerm|s3`. It has no apply step.

The first real DEV plan/apply must verify effective privileges rather than widening `AR_TERRAFORM_DEV` pre-emptively.

## Employee identity

Terraform defines roles and privileges. Employee joins/leaves should be driven by enterprise IdP/SCIM group membership, not user records in Terraform.
