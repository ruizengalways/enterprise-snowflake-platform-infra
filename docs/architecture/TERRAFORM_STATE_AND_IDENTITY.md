# Terraform State and Workload Identity

## Status

Phase 1 source/static-CI baseline. Azure Blob/S3 backend profiles, platform Terraform WIF, project CI/deployment WIF source, immutable project deployment workflows, and the manual DEV platform-plan path exist. No real remote state or Snowflake identity has been applied yet.

## Control-plane principle

Terraform state, platform Terraform identity and project delivery identities are separate concerns:

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
├── OIDC -> SU_GITHUB_<DOMAIN>_CI
│          -> AR_<DOMAIN>_CI
│          -> PR workspace lifecycle
│
└── OIDC -> SU_GITHUB_<DOMAIN>_DEPLOY
           -> AR_<DOMAIN>_DEPLOY
           -> stable DEV/UAT/PROD project deployment
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

There are ten independent lifecycle state objects:

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

Why project identities are separate from platform state:

```text
identity/<env>
  creates platform Terraform identity
        ↓
platform/<env>
  creates AR_<DOMAIN>_DEPLOY
  DEV also creates AR_<DOMAIN>_CI
        ↓
project-identity/<env>
  creates project service users and WIF trusts
  bound to those existing machine roles
```

Combining these lifecycles would make routine platform state own delivery identities and blur bootstrap authority. Each root uses the same selectable backend adapter but a distinct state key.

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

## Project workload identities

Roots:

```text
terraform/stacks/project-identity/dev/
terraform/stacks/project-identity/uat/
terraform/stacks/project-identity/prod/
```

Generic identity-only module:

```text
terraform/modules/service-identity/
```

DEV creates both PR-CI and stable deployment identities:

```text
SU_GITHUB_HEALTH_CI      -> AR_HEALTH_CI
SU_GITHUB_TRANSPORT_CI   -> AR_TRANSPORT_CI
SU_GITHUB_HEALTH_DEPLOY  -> AR_HEALTH_DEPLOY
SU_GITHUB_TRANSPORT_DEPLOY -> AR_TRANSPORT_DEPLOY
```

UAT and PROD create deployment identities only:

```text
SU_GITHUB_<DOMAIN>_DEPLOY -> AR_<DOMAIN>_DEPLOY
```

The module creates only the Snowflake SERVICE user/WIF trust and grants an existing account role. Role capabilities remain owned by platform RBAC Terraform.

Execution dependency:

```text
platform/<env> -> project-identity/<env>
```

The platform root must create `AR_<DOMAIN>_DEPLOY` first. In DEV it also creates `AR_<DOMAIN>_CI` before project identities are bootstrapped.

Project OIDC subjects are analytics-repository + GitHub Environment scoped, for example:

```text
repo:ruizengalways/enterprise-snowflake-health-analytics:environment:ci
repo:ruizengalways/enterprise-snowflake-health-analytics:environment:dev
repo:ruizengalways/enterprise-snowflake-health-analytics:environment:uat
repo:ruizengalways/enterprise-snowflake-health-analytics:environment:prod
```

Transport uses the Transport repository in the same pattern. A Health workflow therefore cannot authenticate as a Transport workload identity.

## Account-scoped OIDC audience

Platform and project identities require a non-empty account-scoped Snowflake OIDC audience. The shared `snowflakecomputing.com` audience is rejected by the Terraform modules.

Reusable project workflows explicitly request a GitHub OIDC token with the configured account-scoped audience and pass the short-lived token to Snowflake/dbt. This preserves the account boundary without storing a password/private key.

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
dev
uat
prod
```

Each project environment used for Snowflake workload identity must define:

```text
SNOWFLAKE_ACCOUNT
SNOWFLAKE_OIDC_AUDIENCE
```

The Snowflake service user, role, warehouse and database are convention-derived from domain code and target environment by the reusable framework workflows.

Use environment protection/review rules appropriate to risk. PROD should require stronger approval than DEV; repository branches do not represent environments.

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
4. requests a custom-audience GitHub OIDC token;
5. connects as `SU_GITHUB_<DOMAIN>_CI` with `AR_<DOMAIN>_CI`;
6. executes only the generated local workspace SQL;
7. creates on PR open/reopen/synchronize and drops on PR close.

It does not execute untrusted project PR business code under Snowflake credentials.

## Stable project deployment workflow

Framework:

```text
enterprise-snowflake-data-project-framework/.github/workflows/project-deploy.yml
```

Health and Transport expose thin manual callers. The reusable workflow:

1. accepts only `dev`, `uat` or `prod`;
2. requires a full 40-character project Git SHA;
3. requires a full 40-character framework SHA;
4. checks out both immutable revisions;
5. verifies the project's dbt package pin matches the framework deployment SHA;
6. targets the corresponding protected GitHub Environment;
7. requests an account-scoped OIDC token;
8. connects as `SU_GITHUB_<DOMAIN>_DEPLOY` / `AR_<DOMAIN>_DEPLOY`;
9. runs dbt against `<ENV>_<DOMAIN>` on `WH_<DOMAIN>_TRANSFORM`.

Promotion therefore changes the target environment, not the code revision. The same project SHA can be promoted DEV -> UAT -> PROD.

## Real execution order

```text
remote state control plane
-> organization bootstrap/import

DEV:
   identity/dev
-> platform/dev plan/apply/verify
-> project-identity/dev
-> configure project GitHub Environments ci + dev
-> real PR workspace create/drop test
-> real DEV immutable project deployment test

UAT:
   identity/uat
-> platform/uat plan/apply/verify
-> project-identity/uat
-> configure project GitHub Environment uat
-> promote an already-verified project Git SHA

PROD:
   identity/prod
-> platform/prod protected plan/apply/verify
-> project-identity/prod
-> configure protected project GitHub Environment prod
-> promote the exact approved project Git SHA
```

Human UAT/PROD transform warehouse access is not part of this routine path. Emergency execution is JIT/break-glass through enterprise identity governance.

## References

- ADR-023 — platform Terraform GitHub OIDC identity.
- ADR-024 — Azure Blob/S3 backend adapters.
- ADR-025 — DEV personal and PR CI workspace lifecycle.
- ADR-027 — project workload OIDC identity lifecycle.
- `docs/CURRENT_CONTEXT.md`
- `docs/runbooks/terraform-platform-bootstrap.md`
