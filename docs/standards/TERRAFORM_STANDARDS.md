# Terraform Standards

## Scope

These standards apply to `enterprise-snowflake-platform-infra`.

## Version policy

- Terraform CLI is pinned by `.terraform-version`.
- Snowflake provider is pinned exactly in each root stack.
- Current baseline: Terraform `1.16.0`, `snowflakedb/snowflake` provider `2.19.0`.
- Provider upgrades require migration-guide review and CI validation.
- `.terraform.lock.hcl` is committed for every root and CI uses `-lockfile=readonly`.

## Authentication

Never place passwords, private keys, OAuth tokens, PATs or cloud access keys in Git.

Routine DEV/UAT/PROD roots expose lifecycle provider aliases:

```text
snowflake.objects
snowflake.security
```

Both aliases run under:

```text
DEV  -> AR_TERRAFORM_DEV
UAT  -> AR_TERRAFORM_UAT
PROD -> AR_TERRAFORM_PROD
```

GitHub -> Snowflake authentication uses Workload Identity Federation with GitHub OIDC:

```text
SU_GITHUB_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD
```

`ACCOUNTADMIN` is permitted only in the separate identity bootstrap lifecycle. Organization account creation uses the separate organization bootstrap provider authority.

## Privileged bootstrap boundaries

Organization root:

```text
terraform/stacks/organization/
```

Identity roots:

```text
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
```

Normal DEV/UAT/PROD roots never create Snowflake accounts or their own authentication identity.

## Routine Terraform role privileges

Initial account-level privileges are deliberately explicit:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Do not grant ACCOUNTADMIN, SYSADMIN or SECURITYADMIN to routine GitHub Terraform users. Add another privilege only when an implemented Terraform-owned capability demonstrates the requirement.

`MANAGE GRANTS` is powerful; `AR_TERRAFORM_<ENV>` is machine-only and never a domain/human role.

## Remote state

Terraform state is never committed.

The platform is **state-backend agnostic**. Supported reference profiles are:

```text
azurerm  -> Azure Blob Storage
s3       -> Amazon S3
```

Azure Blob is the current Microsoft-first reference example; S3 is retained for AWS-centred organisations.

Terraform backend type cannot be selected from an input variable. Therefore normal roots contain no committed backend block. At execution time:

```bash
bash terraform/scripts/select-backend.sh <azurerm|s3> terraform/stacks/<root>
```

materialises an ignored `backend.generated.tf` from `terraform/backend-profiles/`.

### Azure Blob rules

Use Microsoft Entra ID with GitHub OIDC / workload identity federation for new CI workloads.

Baseline:

```text
ARM_USE_OIDC=true
ARM_USE_AZUREAD=true
Storage Blob Data Contributor scoped to the state container
```

Do not introduce an Azure client secret merely to access Terraform state.

Azure Blob native state locking/consistency is used; no separate lock database is required.

### S3 rules

Use GitHub OIDC -> AWS IAM, bucket versioning, server-side encryption, blocked public access and restricted object-prefix permissions.

The S3 profile sets:

```text
use_lockfile = true
```

Do not add DynamoDB locking for new deployments; Terraform marks that S3 locking mode deprecated.

### OneDrive / SharePoint rule

OneDrive/SharePoint may hold architecture documents, runbooks, approvals and audit evidence. A synchronised folder must not be the authoritative location for collaborative live `terraform.tfstate`.

### State boundaries

Whichever backend is selected, retain:

```text
enterprise-snowflake-platform-infra/organization/terraform.tfstate
enterprise-snowflake-platform-infra/identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/identity/uat/terraform.tfstate
enterprise-snowflake-platform-infra/identity/prod/terraform.tfstate
enterprise-snowflake-platform-infra/platform/dev/terraform.tfstate
enterprise-snowflake-platform-infra/platform/uat/terraform.tfstate
enterprise-snowflake-platform-infra/platform/prod/terraform.tfstate
```

Do not make both Azure Blob and S3 simultaneously writable sources of truth for the same state. Backend migration is an explicit Terraform migration operation.

See ADR-024 and `docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`.

## Root stack pattern

Current roots:

```text
terraform/stacks/organization/
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
terraform/stacks/dev/
terraform/stacks/uat/
terraform/stacks/prod/
```

Routine account roots:

1. pin Terraform/provider versions and committed lock files;
2. use `AR_TERRAFORM_<ENV>`;
3. read YAML from `config/environments/`;
4. compose reusable modules;
5. contain no credentials;
6. expose useful outputs;
7. contain no domain business logic.

Identity roots are separate because routine automation must not own the state that can destroy its own authentication path.

## Module pattern

Current modules:

- `analytics-environment` — one domain analytics database plus stable schemas;
- `warehouse` — standard warehouse guardrails;
- `platform-control` — account-local `PLATFORM_CONTROL` database/schemas;
- `rbac` — platform/domain account roles, database roles, guest/read/write access and warehouse grants;
- `workload-identity` — Snowflake service user + dedicated routine Terraform role + GitHub OIDC trust.

A database passed to RBAC has exactly one owning domain through `database_projects`. Do not recreate a domain × database Cartesian product.

Published consumer schemas are passed through `published_schemas_by_database`; they must be a subset of stable schemas and initially represent `MARTS` and `SEMANTIC`.

Do not create a module only to wrap a single line or hide genuine business differences.

## OIDC rules

GitHub Environments are named exactly:

```text
dev
uat
prod
```

Snowflake OIDC subjects are pinned to repository + environment, for example:

```text
repo:ruizengalways/enterprise-snowflake-platform-infra:environment:dev
```

Use an account-scoped `SNOWFLAKE_OIDC_AUDIENCE`; do not use the shared `snowflakecomputing.com` audience for these Terraform identities.

The Snowflake provider experiment `USER_ENABLE_DEFAULT_WORKLOAD_IDENTITY` is enabled only in identity bootstrap roots.

## Human access boundary

Terraform defines roles, hierarchy, database privileges and warehouse grants. It does **not** manage day-to-day employee membership.

Target enterprise flow:

```text
Entra ID / Okta group membership
    -> SCIM / approved identity provisioning
        -> AR_<DOMAIN>_<CAPABILITY>
```

Joining a new employee to an existing domain should not require Terraform knowledge.

## Resource ownership

Terraform owns selected stable platform infrastructure/RBAC. It does not own dbt models, business transformations, employee lifecycle records or routine data changes.

One Snowflake object has one authoritative owner.

## Naming and metadata

Database pattern:

```text
<ENVIRONMENT>_<DOMAIN>
```

Domain role hierarchy:

```text
AR_<DOMAIN>_GUEST -> READER -> DEVELOPER -> ADMIN
```

Database-role hierarchy:

```text
DR_<DOMAIN>_ANALYTICS_GUEST -> READ -> WRITE -> OWNER
```

Warehouse pattern:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV only
```

Credentials are never configuration metadata.

## Warehouse defaults

Baseline warehouses use conservative settings unless evidence requires otherwise:

- standard warehouse type;
- `XSMALL` initial size;
- auto-resume enabled;
- auto-suspend normally 60 seconds;
- initially suspended;
- explicit statement timeout;
- no query acceleration by default;
- no multi-cluster scaling without evidence.

Cost/resource monitors remain a later Phase 1 capability.

## Validation

Every Terraform change must pass:

```text
terraform fmt -check -recursive
terraform init -backend=false -input=false -lockfile=readonly
terraform validate
```

Current CI targets all seven roots and additionally materialises/validates both `azurerm` and `s3` backend profiles without making cloud connections.

Remote plan is separate from static CI. `terraform-plan-dev.yml` is manual-only and requires one real remote state backend plus Snowflake WIF configuration before it can execute.

No automated apply is enabled yet.
