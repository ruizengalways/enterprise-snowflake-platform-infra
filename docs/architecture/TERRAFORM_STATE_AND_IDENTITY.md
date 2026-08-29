# Terraform State and Workload Identity

## Status

Phase 1 source/static-CI baseline. Azure Blob/S3 backend profiles, platform Terraform WIF, project CI/deployment WIF source, immutable project deployment workflows and the manual DEV platform-plan path exist. No real remote state or Snowflake workload identity has been applied yet.

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
│          -> DEV PR workspace lifecycle
│
└── OIDC -> SU_GITHUB_<DOMAIN>_DEPLOY
           -> AR_<DOMAIN>_DEPLOY
           -> stable DEV/UAT/PROD project deployment
```

Changing the Terraform state backend does not change Snowflake RBAC/domain design.

## Backend selection

Terraform backend type is selected at execution time because backend type cannot be parameterized through a normal Terraform input variable:

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

Azure Blob is the Microsoft-first reference. S3 remains a supported AWS reference. OneDrive/SharePoint may hold human-facing documentation/evidence but is not authoritative live Terraform state.

A deployment chooses one authoritative writable backend. Do not keep Azure Blob and S3 simultaneously writable for the same state.

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

Per-environment dependency:

```text
identity/<env>
  creates platform Terraform identity
        ↓
platform/<env>
  creates AR_<DOMAIN>_DEPLOY
  DEV also creates AR_<DOMAIN>_CI
        ↓
project-identity/<env>
  creates project service users/WIF trusts
  bound to those existing roles
```

Keeping these lifecycles separate prevents routine platform state from owning the service identities used for project delivery.

## Backend authentication

### Azure Blob

Reference path:

```text
GitHub OIDC -> Microsoft Entra workload federation -> Azure Blob container
```

Baseline backend environment/configuration includes:

```text
ARM_USE_OIDC=true
ARM_USE_AZUREAD=true
AZURE_TENANT_ID / ARM_TENANT_ID
AZURE_CLIENT_ID / ARM_CLIENT_ID
TF_STATE_STORAGE_ACCOUNT
TF_STATE_CONTAINER
```

Baseline data-plane access is `Storage Blob Data Contributor` scoped to the state container. Avoid client secrets for new automation.

### Amazon S3

Reference path:

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

Initial routine privileges:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Routine Terraform does not activate ACCOUNTADMIN, SYSADMIN or SECURITYADMIN. Identity bootstrap may use ACCOUNTADMIN only to establish machine identity/WIF.

Platform OIDC subjects are repository + GitHub Environment scoped:

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
SU_GITHUB_HEALTH_CI         -> AR_HEALTH_CI
SU_GITHUB_TRANSPORT_CI      -> AR_TRANSPORT_CI
SU_GITHUB_HEALTH_DEPLOY     -> AR_HEALTH_DEPLOY
SU_GITHUB_TRANSPORT_DEPLOY  -> AR_TRANSPORT_DEPLOY
```

UAT and PROD create deployment identities only:

```text
SU_GITHUB_<DOMAIN>_DEPLOY -> AR_<DOMAIN>_DEPLOY
```

The module creates only the Snowflake SERVICE user/WIF trust and grants an existing account role. Role capabilities remain owned by platform RBAC Terraform.

Project subjects are analytics-repository + GitHub Environment scoped, for example:

```text
repo:ruizengalways/enterprise-snowflake-health-analytics:environment:ci
repo:ruizengalways/enterprise-snowflake-health-analytics:environment:dev
repo:ruizengalways/enterprise-snowflake-health-analytics:environment:uat
repo:ruizengalways/enterprise-snowflake-health-analytics:environment:prod
```

Transport uses the Transport repository in the same pattern. A Health workflow therefore cannot authenticate as a Transport workload identity.

ADR-027 covers the original DEV PR-CI identity split. ADR-034 extends the model to stable DEV/UAT/PROD deployment identities and machine-only routine transform execution.

## Account-scoped OIDC audience

Platform and project identities require a non-empty account-scoped Snowflake OIDC audience. The shared `snowflakecomputing.com` audience is rejected by the Terraform modules.

Reusable project workflows explicitly request a GitHub OIDC token with the configured account-scoped audience and pass the short-lived token to Snowflake/dbt. No project password/private key is stored.

## GitHub Environments

Platform Infra repository:

```text
dev
uat
prod
```

Health and Transport repositories:

```text
ci
dev
uat
prod
```

Each project environment used for Snowflake workload identity defines:

```text
SNOWFLAKE_ACCOUNT
SNOWFLAKE_OIDC_AUDIENCE
```

Environment-level configuration must be consumed only after the job has entered the target GitHub Environment. Do not pre-bind environment-only variables in a way that evaluates them before the protected environment is active.

Use environment protection/review rules appropriate to risk. PROD should require stronger approval than DEV; repository branches do not represent environments.

## PR workspace workflow

Framework workflow:

```text
enterprise-snowflake-data-project-framework/.github/workflows/pr-workspace.yml
```

Thin project callers are pinned to a full immutable framework SHA. The reusable workflow:

1. targets GitHub Environment `ci`;
2. validates domain/action/framework inputs;
3. renders framework-owned QUERY_TAG/workspace SQL;
4. requests an account-scoped GitHub OIDC token;
5. connects as `SU_GITHUB_<DOMAIN>_CI` with `AR_<DOMAIN>_CI`;
6. executes only generated local workspace SQL;
7. creates on PR open/reopen/synchronize and drops on PR close.

It does not execute untrusted project PR business code under Snowflake credentials.

## Stable project deployment workflow

Framework workflow:

```text
enterprise-snowflake-data-project-framework/.github/workflows/project-deploy.yml
```

Health and Transport expose thin manual callers. The reusable workflow:

1. accepts only `dev`, `uat` or `prod`;
2. requires a full lowercase 40-character project Git SHA;
3. requires a full lowercase 40-character framework Git SHA;
4. checks out full `main` history and proves the requested project SHA is an ancestor of current `main`;
5. checks out that exact project SHA detached;
6. checks out the exact framework SHA;
7. verifies the project `dbt/packages.yml` pin matches the framework SHA;
8. enters the corresponding protected GitHub Environment;
9. reads environment-scoped Snowflake configuration after environment activation;
10. requests the account-scoped OIDC token;
11. connects as `SU_GITHUB_<DOMAIN>_DEPLOY` / `AR_<DOMAIN>_DEPLOY`;
12. runs dbt against `<ENV>_<DOMAIN>` on `WH_<DOMAIN>_TRANSFORM`.

The main-history gate prevents an unmerged side-branch commit from being manually supplied directly to deployment.

Promotion therefore changes the target environment, not the source revision:

```text
same reviewed project SHA
DEV -> UAT -> PROD
```

Deployments to the same project/environment are serialized and do not cancel an older in-flight deployment merely because a newer request appears.

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
-> real immutable main-history DEV project deployment test
-> live framework/SCD behavior verification

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

Human UAT/PROD transform warehouse access is not part of the routine path. Emergency execution is JIT/break-glass through enterprise identity governance.

## References

- ADR-023 — platform Terraform GitHub OIDC identity.
- ADR-024 — Azure Blob/S3 backend adapters.
- ADR-025 — DEV personal and PR workspace lifecycle.
- ADR-027 — DEV PR-CI OIDC identity lifecycle.
- ADR-034 — project deployment identity and immutable promotion.
- `docs/CURRENT_CONTEXT.md`
- `docs/runbooks/terraform-platform-bootstrap.md`
