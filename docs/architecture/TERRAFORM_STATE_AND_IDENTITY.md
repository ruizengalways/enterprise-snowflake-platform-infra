# Terraform State and Workload Identity

## Status

Phase 1 implementation baseline. Source code and static CI are present; remote infrastructure and Snowflake identity bootstrap must still be configured/applied against real accounts.

## Control-plane flow

```text
GitHub Actions
│
├── GitHub OIDC -> AWS IAM role
│                  └── S3 Terraform state + .tflock
│
└── GitHub OIDC -> Snowflake SERVICE user
                   └── AR_TERRAFORM_<ENV>
                       └── routine platform Terraform
```

The AWS and Snowflake trust relationships are independent. No AWS access key, Snowflake password, or Snowflake private key is required for routine CI.

## State layout

One S3 bucket may host the reference platform states, but each lifecycle has its own object key:

```text
organization/terraform.tfstate
identity/dev/terraform.tfstate
identity/uat/terraform.tfstate
identity/prod/terraform.tfstate
platform/dev/terraform.tfstate
platform/uat/terraform.tfstate
platform/prod/terraform.tfstate
```

The full prefix used by workflows is:

```text
enterprise-snowflake-platform-infra/<path-above>
```

The bucket must have:

- versioning enabled;
- encryption enabled;
- public access blocked;
- IAM restricted to the required state and `.tflock` object prefixes;
- appropriate CloudTrail/S3 audit coverage for the hosting organisation;
- a recovery procedure for accidental state overwrite/deletion.

Terraform uses S3 `use_lockfile = true`; do not add DynamoDB locking.

## GitHub Environment variables

Create GitHub Environments named exactly:

```text
dev
uat
prod
```

At minimum, the DEV environment used by `terraform-plan-dev.yml` needs these non-secret variables:

```text
TF_STATE_BUCKET
TF_STATE_REGION
AWS_TERRAFORM_STATE_ROLE_ARN
SNOWFLAKE_ORGANIZATION_NAME
SNOWFLAKE_ACCOUNT_NAME
SNOWFLAKE_OIDC_AUDIENCE
```

`SNOWFLAKE_OIDC_AUDIENCE` must be a non-empty value scoped to the target Snowflake account. The exact value is an operations/security input because the final Snowflake organisation/account identifiers are only known after account bootstrap.

The Snowflake Terraform service-user name is read from `config/environments/<env>.yml`; it is not duplicated as a GitHub variable.

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

Initial identity bootstrap cannot authenticate using the identity it is about to create. Run it from a tightly controlled administrator session against the target account, for example an approved local/administrative Snowflake authentication method with `ACCOUNTADMIN` activated only for this bootstrap operation.

Do not store that bootstrap credential in the repository or convert it into the normal GitHub credential.

Example lifecycle:

```text
1. DEV Snowflake account exists
2. S3 remote state prerequisite exists
3. initialise identity/dev state
4. privileged review + plan identity/dev
5. apply identity/dev
6. verify SU_GITHUB_TERRAFORM_DEV and AR_TERRAFORM_DEV
7. configure GitHub Environment dev variables / AWS OIDC state role
8. run Terraform Plan DEV workflow
9. review DEV platform plan
10. only then introduce a protected DEV apply workflow
```

Repeat for UAT only after DEV is proven, then PROD.

## Routine Snowflake privileges

`AR_TERRAFORM_<ENV>` currently receives:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

It does not receive `ACCOUNTADMIN`, `SYSADMIN`, or `SECURITYADMIN` as routine execution authority.

The role owns objects it creates and can administer grants required by the platform. Because `MANAGE GRANTS` is powerful, this role is dedicated exclusively to Terraform automation and is never a human/domain application role.

## GitHub OIDC subjects

```text
DEV  repo:ruizengalways/enterprise-snowflake-platform-infra:environment:dev
UAT  repo:ruizengalways/enterprise-snowflake-platform-infra:environment:uat
PROD repo:ruizengalways/enterprise-snowflake-platform-infra:environment:prod
```

Jobs must set the matching GitHub `environment:`; changing that changes GitHub's OIDC subject and should intentionally break Snowflake authentication until the trust configuration is reviewed.

## DEV plan workflow

`.github/workflows/terraform-plan-dev.yml` is manual-only.

It:

1. enters GitHub Environment `dev`;
2. obtains short-lived AWS credentials via GitHub OIDC for S3 state;
3. requests a GitHub OIDC token with `SNOWFLAKE_OIDC_AUDIENCE`;
4. authenticates the Snowflake Terraform provider using WIF;
5. initialises the DEV S3 state key;
6. validates;
7. runs `terraform plan` only.

It intentionally does not apply and does not upload a binary Terraform plan artifact.

## Promotion of infrastructure automation

Do not create generic UAT/PROD apply automation before the preceding boundary is proven:

```text
DEV identity + plan + apply + verification
       ↓
UAT identity + plan + apply + verification
       ↓
PROD identity + protected plan/apply
```

GitHub Environment approval rules are part of the deployment control plane, especially for PROD.

## References

- ADR-022 — S3 remote state with independent lifecycle boundaries.
- ADR-023 — GitHub OIDC workload identity for routine Terraform.
- `docs/architecture/ACCOUNT_TOPOLOGY.md`
- `docs/architecture/RBAC_MODEL.md`
- `docs/standards/TERRAFORM_STANDARDS.md`
