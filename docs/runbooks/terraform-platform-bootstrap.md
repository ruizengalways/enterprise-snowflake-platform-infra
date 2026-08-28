# Terraform Platform Bootstrap Runbook

## Purpose

Execute the Phase 1 control-plane bootstrap without mixing organization authority, Terraform identity bootstrap, and routine platform infrastructure state.

This runbook assumes the source/static CI baseline is already green. It does **not** contain real credentials or account identifiers.

## Safety rules

- Never commit Snowflake private keys/passwords, AWS access keys, OIDC tokens, Terraform state, or real `.tfvars`.
- Organization, identity and routine platform roots use separate state keys.
- Organization bootstrap may use ORGADMIN only for account lifecycle.
- Identity bootstrap may use ACCOUNTADMIN only to establish the dedicated routine Terraform identity.
- Routine platform Terraform uses only `AR_TERRAFORM_<ENV>`.
- Start with DEV. Do not enable UAT/PROD apply before the preceding environment is verified.
- Do not run `terraform destroy` against organization or identity bootstrap roots.

## 1. External S3 state prerequisite

Provision one control-plane S3 bucket outside these Terraform roots with:

- versioning enabled;
- server-side encryption enabled;
- public access blocked;
- audit logging appropriate to the hosting AWS account;
- GitHub OIDC IAM trust for this repository;
- IAM permissions restricted to the required state object and `.tflock` prefixes.

Reference state keys:

```text
enterprise-snowflake-platform-infra/organization/terraform.tfstate
enterprise-snowflake-platform-infra/identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/identity/uat/terraform.tfstate
enterprise-snowflake-platform-infra/identity/prod/terraform.tfstate
enterprise-snowflake-platform-infra/platform/dev/terraform.tfstate
enterprise-snowflake-platform-infra/platform/uat/terraform.tfstate
enterprise-snowflake-platform-infra/platform/prod/terraform.tfstate
```

Terraform uses S3 native locking (`use_lockfile = true`).

## 2. Define shell inputs locally

Use environment variables or another approved secret/config mechanism. Example variable names only:

```bash
export TF_STATE_BUCKET="<state-bucket>"
export TF_STATE_REGION="<aws-region>"

export SNOWFLAKE_ORGANIZATION_NAME="<snowflake-organization>"
export DEV_SNOWFLAKE_ACCOUNT_NAME="<dev-account-name>"
export UAT_SNOWFLAKE_ACCOUNT_NAME="<uat-account-name>"
export PROD_SNOWFLAKE_ACCOUNT_NAME="<prod-account-name>"
```

Do not put these values into committed `.tfvars` merely for convenience.

## 3. Organization account bootstrap/import

If DEV/UAT/PROD do not exist, initialize the organization root:

```bash
terraform -chdir=terraform/stacks/organization init \
  -lockfile=readonly \
  -backend-config="bucket=${TF_STATE_BUCKET}" \
  -backend-config="key=enterprise-snowflake-platform-infra/organization/terraform.tfstate" \
  -backend-config="region=${TF_STATE_REGION}"
```

Supply `initial_admin_name`, `initial_admin_email`, and `initial_admin_rsa_public_key` through the approved bootstrap input mechanism, authenticate to the organization account with controlled ORGADMIN authority, then:

```bash
terraform -chdir=terraform/stacks/organization plan
```

Review every account action before apply.

If DEV/UAT/PROD already exist, import them into this root rather than creating duplicates. Match `config/organization.yml` to reality before import.

## 4. Verify account creation/import

From an approved organization administration session, verify the three target accounts exist and record their actual Snowflake organization/account names required by provider authentication.

Do not proceed using guessed identifiers.

## 5. Choose DEV Snowflake OIDC audience

Define a non-empty audience scoped to the DEV Snowflake account and use the **same exact value** in:

1. `identity/dev` variable `oidc_audience`;
2. GitHub Environment `dev` variable `SNOWFLAKE_OIDC_AUDIENCE`;
3. the GitHub OIDC token request performed by `terraform-plan-dev.yml`.

Do not use the shared `snowflakecomputing.com` audience for the platform Terraform identities.

## 6. Bootstrap DEV Terraform identity

Authenticate to the DEV Snowflake account using a controlled administrator method with ACCOUNTADMIN available for this bootstrap only.

Initialize identity state:

```bash
terraform -chdir=terraform/stacks/identity/dev init \
  -lockfile=readonly \
  -backend-config="bucket=${TF_STATE_BUCKET}" \
  -backend-config="key=enterprise-snowflake-platform-infra/identity/dev/terraform.tfstate" \
  -backend-config="region=${TF_STATE_REGION}"
```

Plan with the chosen audience:

```bash
terraform -chdir=terraform/stacks/identity/dev plan \
  -var="oidc_audience=<dev-account-scoped-audience>"
```

Expected identity resources include:

```text
SU_GITHUB_TERRAFORM_DEV
AR_TERRAFORM_DEV
GitHub OIDC workload identity trust
role grant to the service user
```

Review and apply only this identity root before attempting routine DEV Terraform.

## 7. Verify DEV Terraform identity in Snowflake

Use administrator access to verify:

```sql
SHOW USERS LIKE 'SU_GITHUB_TERRAFORM_DEV';
SHOW ROLES LIKE 'AR_TERRAFORM_DEV';
SHOW GRANTS TO ROLE AR_TERRAFORM_DEV;
SHOW GRANTS TO USER SU_GITHUB_TERRAFORM_DEV;
```

Expected initial routine account privileges:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

Do not add SYSADMIN/SECURITYADMIN/ACCOUNTADMIN merely to make the first plan easier.

## 8. Configure GitHub Environment `dev`

Create/protect GitHub Environment:

```text
dev
```

Set these environment variables:

```text
TF_STATE_BUCKET
TF_STATE_REGION
AWS_TERRAFORM_STATE_ROLE_ARN
SNOWFLAKE_ORGANIZATION_NAME
SNOWFLAKE_ACCOUNT_NAME
SNOWFLAKE_OIDC_AUDIENCE
```

For DEV, `SNOWFLAKE_ACCOUNT_NAME` is the actual DEV Snowflake account name, not `DEV_HEALTH` or another database name.

The service-user name does not need to be duplicated in GitHub; the workflow reads it from `config/environments/dev.yml`.

## 9. Test AWS state OIDC independently

Before blaming Terraform or Snowflake, verify the GitHub `dev` environment can assume the configured AWS state role and access only the intended DEV state/lock prefix.

The IAM role should not receive broad unrelated S3 privileges.

## 10. Run manual DEV remote plan

Run the GitHub workflow:

```text
Terraform Plan DEV
```

It should:

```text
GitHub OIDC -> AWS IAM -> S3 platform/dev state
GitHub OIDC -> SU_GITHUB_TERRAFORM_DEV -> AR_TERRAFORM_DEV
terraform init -> validate -> plan
```

There is intentionally no apply step.

## 11. Review the DEV plan

Confirm the plan contains only expected Platform Infra objects such as:

- `DEV_HEALTH`, `CI_HEALTH`, `DEV_TRANSPORT`, `CI_TRANSPORT`;
- stable transformation schemas in DEV domain databases;
- `PLATFORM_CONTROL` structural schemas;
- domain/platform account roles;
- domain database roles and grants;
- domain QUERY/TRANSFORM/CI warehouses and `WH_PLATFORM_OPS`.

It must not unexpectedly create human users, project business tables/models, Kafka/Openflow/Snowpipe resources, or PROD objects.

If Snowflake denies a privilege, record the exact resource/action and add only the minimum demonstrated privilege to `AR_TERRAFORM_DEV`. Do not fall back to a system role as the routine solution.

## 12. Enable DEV apply only after plan review

A protected `terraform-apply-dev.yml` does not exist yet by design.

Only add it after:

1. remote state works;
2. Snowflake WIF succeeds;
3. DEV plan is reviewed;
4. least-privilege gaps are understood;
5. an approval/control mechanism is chosen.

The apply workflow must rerun/validate against the intended commit and must not trust an unreviewed stale plan artifact.

## 13. Post-apply Snowflake verification

After a reviewed DEV apply, verify at minimum:

```sql
SHOW DATABASES LIKE 'DEV_%';
SHOW DATABASES LIKE 'CI_%';
SHOW WAREHOUSES LIKE 'WH_%';
SHOW ROLES LIKE 'AR_%';
```

For each domain database, inspect database roles and grants. Validate explicitly that:

- Health roles do not grant Transport authority;
- Transport roles do not grant Health authority;
- GUEST sees only MARTS/SEMANTIC in stable DEV databases;
- GUEST sees no CI database;
- DEVELOPER has WRITE only in DEV;
- CI warehouses are not granted to human domain roles.

Capture discrepancies before moving to UAT.

## 14. UAT and PROD progression

Only after DEV is proven:

```text
identity/uat -> UAT plan -> protected UAT apply -> verify
        ↓
identity/prod -> protected PROD plan/apply -> verify
```

PROD GitHub Environment should require stronger review/protection than DEV.

## Related documents

- `docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`
- `docs/architecture/ACCOUNT_TOPOLOGY.md`
- `docs/architecture/RBAC_MODEL.md`
- `docs/standards/TERRAFORM_STANDARDS.md`
- ADR-021, ADR-022, ADR-023
