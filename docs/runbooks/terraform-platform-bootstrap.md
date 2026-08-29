# Terraform Platform Bootstrap Runbook

## Purpose

Execute the Phase 1 control-plane bootstrap without mixing organization authority, Terraform identity bootstrap, routine platform infrastructure state, project workload identity bootstrap, or cloud-specific state plumbing.

This runbook assumes source/static CI is already green. It does **not** contain real credentials or account identifiers.

## Safety rules

- Never commit Snowflake private keys/passwords, cloud access keys, OIDC tokens, Terraform state or real `.tfvars`.
- Organization, platform identity, routine platform and project identity roots use separate state keys.
- Organization bootstrap may use ORGADMIN only for account lifecycle.
- Identity bootstrap roots may use ACCOUNTADMIN only to establish dedicated WIF service identities and grants to already-defined machine roles.
- Routine platform Terraform uses only `AR_TERRAFORM_<ENV>`.
- Routine project delivery uses only `AR_<DOMAIN>_CI` or `AR_<DOMAIN>_DEPLOY` as appropriate.
- Start with DEV. Do not enable UAT/PROD apply before the preceding environment is verified.
- Do not run `terraform destroy` against organization or identity bootstrap roots.
- Choose one authoritative remote-state backend for a deployment. Do not make Azure Blob and S3 simultaneous writable copies of the same state.
- UAT/PROD human transform compute is not a standing baseline grant. Emergency execution must be JIT/break-glass through enterprise identity governance.
- Stable project deployment accepts only a reviewed commit that belongs to project `main` history; never bypass this with an unmerged side-branch SHA.

## 1. Choose the remote-state backend

Supported profiles:

```text
azurerm  -> Azure Blob Storage (Microsoft-first reference)
s3       -> Amazon S3 (AWS reference)
```

OneDrive/SharePoint is for human-facing collaboration artifacts, not live Terraform state.

### Option A — Azure Blob Storage

Provision a control-plane Storage Account/container outside these Terraform roots with:

- appropriate redundancy/recovery for the organisation;
- public access disabled;
- Microsoft Entra workload federation from GitHub Actions;
- `Storage Blob Data Contributor` scoped to the state container for the GitHub workload identity;
- diagnostic/audit controls appropriate to the organisation.

Routine CI uses OIDC; do not create an Azure client secret just for Terraform state.

### Option B — Amazon S3

Provision a control-plane S3 bucket outside these Terraform roots with:

- versioning enabled;
- server-side encryption enabled;
- public access blocked;
- GitHub OIDC IAM trust;
- IAM permissions restricted to required state and `.tflock` prefixes;
- audit/recovery controls appropriate to the hosting AWS account.

Terraform uses S3 native `use_lockfile = true`. Do not add DynamoDB locking for a new deployment.

## 2. State keys

Whichever backend is selected, retain these independent lifecycle states:

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

Do not merge project workload identities into routine platform state. The platform root creates the machine roles; the project-identity root creates WIF service users that bind to those existing roles.

## 3. Materialise the backend profile

Terraform backend type cannot be selected with a Terraform variable. Before a remote `terraform init`, generate the ignored backend declaration:

```bash
bash terraform/scripts/select-backend.sh azurerm terraform/stacks/organization
```

or:

```bash
bash terraform/scripts/select-backend.sh s3 terraform/stacks/organization
```

Repeat for the specific root you are about to initialise, including `project-identity/<env>`. `backend.generated.tf` must remain uncommitted.

## 4. Define local/control-plane inputs

### Azure example

```bash
export TF_STATE_BACKEND="azurerm"
export AZURE_TENANT_ID="<tenant-id>"
export AZURE_CLIENT_ID="<federated-app-or-managed-identity-client-id>"
export TF_STATE_STORAGE_ACCOUNT="<storage-account>"
export TF_STATE_CONTAINER="<container>"
```

### S3 example

```bash
export TF_STATE_BACKEND="s3"
export TF_STATE_BUCKET="<state-bucket>"
export TF_STATE_REGION="<aws-region>"
```

Common Snowflake values:

```bash
export SNOWFLAKE_ORGANIZATION_NAME="<snowflake-organization>"
export DEV_SNOWFLAKE_ACCOUNT_NAME="<dev-account-name>"
export UAT_SNOWFLAKE_ACCOUNT_NAME="<uat-account-name>"
export PROD_SNOWFLAKE_ACCOUNT_NAME="<prod-account-name>"
```

Do not place these values into committed `.tfvars` merely for convenience.

## 5. Backend-specific init command

### Azure Blob

The GitHub workflow uses:

```text
ARM_USE_OIDC=true
ARM_USE_AZUREAD=true
ARM_TENANT_ID=<tenant>
ARM_CLIENT_ID=<client-id>
```

Then initialise a root with:

```bash
terraform -chdir=terraform/stacks/organization init \
  -lockfile=readonly \
  -backend-config="storage_account_name=${TF_STATE_STORAGE_ACCOUNT}" \
  -backend-config="container_name=${TF_STATE_CONTAINER}" \
  -backend-config="key=enterprise-snowflake-platform-infra/organization/terraform.tfstate"
```

For standard Blob endpoints, a subscription/resource-group lookup is not required by the backend data-plane path.

### Amazon S3

```bash
terraform -chdir=terraform/stacks/organization init \
  -lockfile=readonly \
  -backend-config="bucket=${TF_STATE_BUCKET}" \
  -backend-config="key=enterprise-snowflake-platform-infra/organization/terraform.tfstate" \
  -backend-config="region=${TF_STATE_REGION}"
```

Use the matching independent state key when initialising another root.

## 6. Organization account bootstrap/import

If DEV/UAT/PROD do not exist, authenticate to the organization account through a controlled ORGADMIN path and plan `terraform/stacks/organization`.

Supply `initial_admin_name`, `initial_admin_email` and `initial_admin_rsa_public_key` through the approved bootstrap input mechanism.

```bash
terraform -chdir=terraform/stacks/organization plan
```

Review every account action before apply.

If DEV/UAT/PROD already exist, import them into this root rather than creating duplicates. Match `config/organization.yml` to reality before import.

## 7. Verify Snowflake account identifiers

From an approved organization administration session, verify the target accounts exist and record their actual Snowflake organization/account names.

Do not proceed using guessed identifiers. `DEV_HEALTH` is a database name, not a Snowflake account name.

## 8. Choose DEV Snowflake OIDC audience

Define a non-empty audience scoped to the DEV Snowflake account and use the same exact value for all DEV Snowflake workload identities and their GitHub Environment token requests.

At minimum this includes:

1. `identity/dev` variable `oidc_audience`;
2. `project-identity/dev` variable `oidc_audience`;
3. Platform Infra GitHub Environment `dev` variable `SNOWFLAKE_OIDC_AUDIENCE`;
4. Health/Transport GitHub Environments `ci` and `dev` variables `SNOWFLAKE_OIDC_AUDIENCE`.

Do not use the shared `snowflakecomputing.com` audience.

## 9. Bootstrap DEV Terraform identity

Authenticate to the DEV Snowflake account using a controlled administrator method with ACCOUNTADMIN available for this bootstrap only.

Select the same state backend for `identity/dev`, initialise its independent key, then plan:

```bash
terraform -chdir=terraform/stacks/identity/dev plan \
  -var="oidc_audience=<dev-account-scoped-audience>"
```

Expected identity resources:

```text
SU_GITHUB_TERRAFORM_DEV
AR_TERRAFORM_DEV
GitHub OIDC workload identity trust
role grant to the service user
```

Review and apply only this identity root before routine DEV Terraform.

## 10. Verify DEV Terraform identity

```sql
SHOW USERS LIKE 'SU_GITHUB_TERRAFORM_DEV';
SHOW ROLES LIKE 'AR_TERRAFORM_DEV';
SHOW GRANTS TO ROLE AR_TERRAFORM_DEV;
SHOW GRANTS TO USER SU_GITHUB_TERRAFORM_DEV;
```

Expected routine account privileges:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Do not add SYSADMIN/SECURITYADMIN/ACCOUNTADMIN merely to make the first plan easier.

## 11. Configure Platform Infra GitHub Environment `dev`

Create/protect:

```text
dev
```

Common variables:

```text
TF_STATE_BACKEND              # azurerm or s3; blank currently defaults to azurerm
SNOWFLAKE_ORGANIZATION_NAME
SNOWFLAKE_ACCOUNT_NAME
SNOWFLAKE_OIDC_AUDIENCE
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

The Snowflake service-user name is read from `config/environments/dev.yml`; do not duplicate it as a GitHub variable.

## 12. Test state OIDC independently

Before blaming Snowflake/Terraform logic, prove the GitHub `dev` environment can reach only the intended remote-state boundary.

Azure path:

```text
GitHub OIDC -> Entra federated identity -> Blob container
```

S3 path:

```text
GitHub OIDC -> AWS IAM role -> required S3 state/lock prefix
```

Avoid broad cloud permissions.

## 13. Run manual DEV remote plan

Run:

```text
Terraform Plan DEV
```

Azure example:

```text
GitHub OIDC -> Azure Blob platform/dev state
GitHub OIDC -> SU_GITHUB_TERRAFORM_DEV -> AR_TERRAFORM_DEV
terraform init -> validate -> plan
```

S3 is the same except the state branch is AWS IAM -> S3.

There is intentionally no apply step.

## 14. Review the DEV plan

Confirm expected Platform Infra objects only:

- `DEV_HEALTH`, `CI_HEALTH`, `DEV_TRANSPORT`, `CI_TRANSPORT`;
- stable DEV transformation schemas;
- `PLATFORM_CONTROL` structural schemas;
- domain/platform human roles;
- `AR_<DOMAIN>_CI` and `AR_<DOMAIN>_DEPLOY` machine roles;
- domain database roles and grants;
- domain QUERY/TRANSFORM/CI warehouses and `WH_PLATFORM_OPS`.

It must not unexpectedly create employee users, project business tables/models, Kafka/Openflow/Snowpipe resources or PROD objects.

If Snowflake denies a privilege, record the exact resource/action and add only the minimum demonstrated privilege to `AR_TERRAFORM_DEV`.

## 15. Enable DEV apply only after plan review

A protected `terraform-apply-dev.yml` does not exist yet by design.

Only add it after:

1. remote state works;
2. Snowflake WIF succeeds;
3. DEV plan is reviewed;
4. least-privilege gaps are understood;
5. an approval/control mechanism is chosen.

## 16. Post-apply DEV platform verification

After a reviewed DEV apply:

```sql
SHOW DATABASES LIKE 'DEV_%';
SHOW DATABASES LIKE 'CI_%';
SHOW WAREHOUSES LIKE 'WH_%';
SHOW ROLES LIKE 'AR_%';
```

Validate explicitly:

- Health roles do not grant Transport authority;
- Transport roles do not grant Health authority;
- GUEST sees only MARTS/SEMANTIC in stable DEV databases;
- GUEST sees no CI database;
- DEVELOPER has WRITE/TRANSFORM only in DEV;
- CI warehouses are not granted to human domain roles;
- `AR_<DOMAIN>_CI` has its CI warehouse and `EXECUTE TASK` but not serverless `EXECUTE MANAGED TASK`;
- `AR_<DOMAIN>_DEPLOY` has the stable domain WRITE capability, transform warehouse and native Stream/Task/Dynamic Table deployment privileges.

## 17. Bootstrap DEV project workload identities

Only after `platform/dev` has created the target machine roles, initialise the independent project identity root and plan/apply it through the controlled ACCOUNTADMIN bootstrap path:

```bash
bash terraform/scripts/select-backend.sh "${TF_STATE_BACKEND}" terraform/stacks/project-identity/dev

terraform -chdir=terraform/stacks/project-identity/dev init \
  <selected-backend-config-for-project-identity/dev>

terraform -chdir=terraform/stacks/project-identity/dev plan \
  -var="oidc_audience=<dev-account-scoped-audience>"
```

Expected service identities:

```text
SU_GITHUB_HEALTH_CI        -> AR_HEALTH_CI
SU_GITHUB_TRANSPORT_CI     -> AR_TRANSPORT_CI
SU_GITHUB_HEALTH_DEPLOY    -> AR_HEALTH_DEPLOY
SU_GITHUB_TRANSPORT_DEPLOY -> AR_TRANSPORT_DEPLOY
```

Verify with `SHOW USERS` / `SHOW GRANTS TO USER` before testing project workflows. Do not grant human roles or system-admin roles to these service users.

## 18. Configure DEV project GitHub Environments and test delivery

In both Health and Transport repositories configure:

```text
ci
dev
```

Each environment must define the DEV-account values:

```text
SNOWFLAKE_ACCOUNT
SNOWFLAKE_OIDC_AUDIENCE
```

The reusable jobs read these environment-level values only after the protected Environment-backed job starts. Do not duplicate them into unprotected repository-level configuration merely to make expression evaluation easier.

Then verify in this order:

1. PR workspace create/drop authenticates as `SU_GITHUB_<DOMAIN>_CI`;
2. no project PR business code receives Snowflake credentials;
3. manual project deployment is given a full lowercase 40-character project Git SHA from reviewed `main` history;
4. the caller/reusable workflow is pinned to the approved full framework SHA;
5. project `dbt/packages.yml` uses that same framework SHA;
6. deployment proves the requested project SHA is an ancestor of current `main`, then detached-checks out that exact revision;
7. deployment authenticates as `SU_GITHUB_<DOMAIN>_DEPLOY` and targets `DEV_<DOMAIN>` / `WH_<DOMAIN>_TRANSFORM`;
8. a known unmerged side-branch SHA is rejected by the standard deployment path.

Do not promote to UAT merely because static CI is green; prove the real DEV authorization, Environment-variable timing, main-history gate and runtime behavior first.

## 19. UAT progression

After DEV is proven:

```text
identity/uat
  -> platform/uat reviewed plan/apply/verify
  -> project-identity/uat
  -> configure Health/Transport GitHub Environment uat
  -> promote the same already-verified reviewed-main project Git SHA
```

`project-identity/uat` creates only `SU_GITHUB_<DOMAIN>_DEPLOY` identities bound to the UAT `AR_<DOMAIN>_DEPLOY` roles.

UAT human roles have no permanent transform warehouse grant. Any emergency manual execution is JIT/break-glass through the enterprise identity-governance process.

## 20. PROD progression

Only after UAT promotion is verified:

```text
identity/prod
  -> platform/prod protected plan/apply/verify
  -> project-identity/prod
  -> configure protected Health/Transport GitHub Environment prod
  -> promote the exact same approved project Git SHA
```

PROD GitHub Environments should require stronger review/protection than DEV/UAT. Promotion changes the target environment, not the code revision. Human ADMIN is not the routine deployment principal and does not receive permanent transform warehouse `USAGE` in the baseline.

## Related documents

- `docs/CURRENT_CONTEXT.md`
- `docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`
- `docs/architecture/ACCOUNT_TOPOLOGY.md`
- `docs/architecture/RBAC_MODEL.md`
- `docs/standards/TERRAFORM_STANDARDS.md`
- ADR-021, ADR-023, ADR-024, ADR-027, ADR-034
