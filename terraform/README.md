# Terraform Platform Foundation

Terraform owns stable Snowflake platform infrastructure selected by the project ownership matrix.

## Layout

```text
terraform/
├── modules/
│   ├── analytics-environment/
│   ├── warehouse/
│   ├── platform-control/
│   ├── rbac/
│   └── workload-identity/
└── stacks/
    ├── organization/
    ├── identity/
    │   ├── dev/
    │   ├── uat/
    │   └── prod/
    ├── dev/
    ├── uat/
    └── prod/
```

Configuration:

```text
config/organization.yml
config/environments/dev.yml
config/environments/uat.yml
config/environments/prod.yml
```

Every root commits its own `.terraform.lock.hcl`. CI uses `terraform init -lockfile=readonly` so dependency drift cannot be silently accepted.

## Versions

```text
Terraform CLI:                  1.16.0
Snowflake Terraform provider:   2.19.0
Provider source:                snowflakedb/snowflake
```

Provider checksums are locked for Linux amd64, macOS amd64 and macOS arm64.

## Bootstrap boundaries

### Organization

`terraform/stacks/organization` is the only root that uses `ORGADMIN`. It creates or imports DEV/UAT/PROD Snowflake accounts. Account resources use `prevent_destroy = true`.

### Workload identity

The separate roots:

```text
terraform/stacks/identity/dev/
terraform/stacks/identity/uat/
terraform/stacks/identity/prod/
```

bootstrap one GitHub OIDC service user and dedicated routine Terraform role per account:

```text
SU_GITHUB_TERRAFORM_DEV  -> AR_TERRAFORM_DEV
SU_GITHUB_TERRAFORM_UAT  -> AR_TERRAFORM_UAT
SU_GITHUB_TERRAFORM_PROD -> AR_TERRAFORM_PROD
```

Identity bootstrap is the only account-level Terraform lifecycle that activates `ACCOUNTADMIN`. It is intentionally separate because routine automation must not own the state capable of destroying its own authentication path.

The provider's `USER_ENABLE_DEFAULT_WORKLOAD_IDENTITY` experiment is confined to these identity roots because Snowflake provider `2.19.0` requires it when managing the service user's `default_workload_identity`.

## Routine provider authority

Routine DEV/UAT/PROD roots do not use Snowflake system roles. Their provider aliases are:

```text
snowflake.objects
snowflake.security
```

Both aliases activate the environment-specific `AR_TERRAFORM_<ENV>` role. Initial account-level privileges are:

```text
CREATE DATABASE
CREATE ROLE
CREATE WAREHOUSE
MANAGE GRANTS
```

That role is machine-only. `MANAGE GRANTS` is broad, so it must never become a human/domain application role.

## Remote state

Reference backend: Amazon S3.

Every root contains only partial backend configuration:

```hcl
terraform {
  backend "s3" {
    encrypt      = true
    use_lockfile = true
  }
}
```

Bucket and region are supplied at init time. DynamoDB locking is not used.

State object keys are separated by lifecycle:

```text
enterprise-snowflake-platform-infra/organization/terraform.tfstate
enterprise-snowflake-platform-infra/identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/identity/uat/terraform.tfstate
enterprise-snowflake-platform-infra/identity/prod/terraform.tfstate
enterprise-snowflake-platform-infra/platform/dev/terraform.tfstate
enterprise-snowflake-platform-infra/platform/uat/terraform.tfstate
enterprise-snowflake-platform-infra/platform/prod/terraform.tfstate
```

The S3 bucket is an external control-plane prerequisite and must have versioning, encryption, public-access blocking, restricted IAM and recovery/audit controls. GitHub accesses it through AWS OIDC rather than static access keys.

See ADR-022 and `docs/architecture/TERRAFORM_STATE_AND_IDENTITY.md`.

## Account and database model

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

Each account also has `PLATFORM_CONTROL`.

A database represents environment × data product/domain, not physical source system. Multiple MSSQL/MySQL/API/file/streaming sources can belong to one domain database, with RAW source schemas added only when those sources are onboarded.

## Domain RBAC

Every domain receives:

```text
AR_<DOMAIN>_GUEST
  -> AR_<DOMAIN>_READER
  -> AR_<DOMAIN>_DEVELOPER
  -> AR_<DOMAIN>_ADMIN
```

Each domain database receives:

```text
DR_<DOMAIN>_ANALYTICS_GUEST
  -> DR_<DOMAIN>_ANALYTICS_READ
  -> DR_<DOMAIN>_ANALYTICS_WRITE
  -> DR_<DOMAIN>_ANALYTICS_OWNER
```

`GUEST` is authenticated read-only consumer access to configured published schemas, initially `MARTS` and `SEMANTIC`. `READER` can inspect all stable layers. DEV developers receive WRITE; UAT/PROD developers remain read-only by default.

## Domain warehouses

Account identifies environment, so normal warehouse names identify domain + workload:

```text
WH_HEALTH_QUERY
WH_HEALTH_TRANSFORM
WH_TRANSPORT_QUERY
WH_TRANSPORT_TRANSFORM
WH_PLATFORM_OPS
```

DEV additionally creates:

```text
WH_HEALTH_CI
WH_TRANSPORT_CI
```

GUEST receives the domain QUERY warehouse. DEV DEVELOPER additionally receives TRANSFORM. UAT/PROD ADMIN currently receives TRANSFORM until project deployment identities take over. CI warehouses are reserved for machine identities.

## Static validation baseline

GitHub Actions successfully executes this baseline across all seven roots:

```text
terraform fmt -check -recursive terraform
terraform init -backend=false -input=false -lockfile=readonly
terraform validate -no-color
```

Current CI matrix:

```text
organization
identity/dev
identity/uat
identity/prod
dev
uat
prod
```

Static validation proves Terraform/provider/schema correctness; it does not prove real Snowflake privileges or remote backend configuration.

## DEV remote-plan spine

`.github/workflows/terraform-plan-dev.yml` is manual-only and has no apply step.

It expects GitHub Environment `dev` variables:

```text
TF_STATE_BUCKET
TF_STATE_REGION
AWS_TERRAFORM_STATE_ROLE_ARN
SNOWFLAKE_ORGANIZATION_NAME
SNOWFLAKE_ACCOUNT_NAME
SNOWFLAKE_OIDC_AUDIENCE
```

The job:

1. obtains short-lived AWS credentials through GitHub OIDC;
2. requests a GitHub OIDC token with the Snowflake account-scoped audience;
3. authenticates Snowflake as `SU_GITHUB_TERRAFORM_DEV` using `WORKLOAD_IDENTITY` / `OIDC`;
4. initialises `platform/dev/terraform.tfstate` in S3;
5. validates and runs `terraform plan`.

It does not upload a binary plan artifact and cannot apply.

## Apply policy

No automated apply is enabled yet. Progression is deliberately:

```text
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

The real DEV plan is expected to surface any privilege gaps that static validation cannot detect. Do not widen `AR_TERRAFORM_DEV` pre-emptively without a demonstrated requirement.

## What the routine baseline creates

### DEV account

- `DEV_HEALTH`, `CI_HEALTH`, `DEV_TRANSPORT`, `CI_TRANSPORT`;
- stable DEV transformation schemas; PR CI schemas stay ephemeral;
- domain GUEST/READER/DEVELOPER/ADMIN roles;
- domain GUEST/READ/WRITE/OWNER database roles;
- Health/Transport QUERY/TRANSFORM/CI warehouses;
- `WH_PLATFORM_OPS`;
- `PLATFORM_CONTROL` plus four structural schemas.

### UAT account

- `UAT_HEALTH`, `UAT_TRANSPORT`;
- stable transformation schemas;
- domain query/transform warehouses plus `WH_PLATFORM_OPS`;
- published-layer GUEST access;
- developers read-only by default.

### PROD account

- `PROD_HEALTH`, `PROD_TRANSPORT`;
- stable transformation schemas;
- domain query/transform warehouses plus `WH_PLATFORM_OPS`;
- published-layer GUEST access;
- developer write disabled.

No ingestion pipelines, dbt models, Snowpipe Streaming, Kafka, Openflow, or speculative operational tables are created by this Terraform slice.
