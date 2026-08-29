# Terraform Platform Bootstrap Runbook

## Purpose

Execute the Phase 1 control-plane bootstrap without mixing organization authority, Terraform identity bootstrap, routine platform infrastructure state, or cloud-specific state plumbing.

This runbook assumes source/static CI is already green. It does **not** contain real credentials or account identifiers.

## Safety rules

- Never commit Snowflake private keys/passwords, cloud access keys, OIDC tokens, Terraform state or real `.tfvars`.
- Organization, identity and routine platform roots use separate state keys.
- Organization bootstrap may use ORGADMIN only for account lifecycle.
- Identity bootstrap may use ACCOUNTADMIN only to establish the dedicated routine Terraform identity.
- Routine platform Terraform uses only `AR_TERRAFORM_<ENV>`.
- Start with DEV. Do not enable UAT/PROD apply before the preceding environment is verified.
- Do not run `terraform destroy` against organization or identity bootstrap roots.
- Choose one authoritative remote-state backend for a deployment. Do not make Azure Blob and S3 simultaneous writable copies of the same state.

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

## 3. Materialise the backend profile

Terraform backend type cannot be selected with a Terraform variable. Before a remote `terraform init`, generate the ignored backend declaration:

```bash
bash terraform/scripts/select-backend.sh azurerm terraform/stacks/organization
```

or:

```bash
bash terraform/scripts/select-backend.sh s3 terraform/stacks/organization
```

Repeat for the specific root you are about to initialise. `backend.generated.tf` must remain uncommitted.

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

Use the matching state key when initialising another root.

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

Define a non-empty audience scoped to the DEV Snowflake account and use the same exact value in:

1. `identity/dev` variable `oidc_audience`;
2. GitHub Environment `dev` variable `SNOWFLAKE_OIDC_AUDIENCE`;
3. the GitHub OIDC token request in `terraform-plan-dev.yml`.

Do not use the shared `snowflakecomputing.com` audience for the platform Terraform identities.

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

## 11. Configure GitHub Environment `dev`

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
- domain/platform account roles;
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

## 16. Post-apply Snowflake verification

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
- DEVELOPER has WRITE only in DEV;
- CI warehouses are not granted to human domain roles.

## 17. UAT and PROD progression

Only after DEV is proven:

```text
identity/uat -> UAT plan -> protected UAT apply -> verify
        ↓
identity/prod -> protected PROD plan/apply -> verify
```

PROD GitHub Environment should require stronger review/protection than DEV.

## Related documents

- `docs/CURRENT_CONTEXT.md`
- `docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`
- `docs/architecture/ACCOUNT_TOPOLOGY.md`
- `docs/architecture/RBAC_MODEL.md`
- `docs/standards/TERRAFORM_STANDARDS.md`
- ADR-021, ADR-023, ADR-024
