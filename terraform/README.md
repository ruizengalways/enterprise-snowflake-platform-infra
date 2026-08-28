# Terraform Platform Foundation

Terraform owns stable Snowflake platform infrastructure selected by the project ownership matrix.

## Layout

```text
terraform/
├── modules/
│   ├── analytics-environment/
│   ├── warehouse/
│   ├── platform-control/
│   └── rbac/
└── stacks/
    ├── dev/
    ├── uat/
    └── prod/
```

Environment metadata:

```text
config/environments/dev.yml
config/environments/uat.yml
config/environments/prod.yml
```

## Versions

```text
Terraform CLI:                  1.16.0
Snowflake Terraform provider:   2.19.0
Provider source:                snowflakedb/snowflake
```

## Account model

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

The account stacks assume the Snowflake accounts already exist. Account creation is a separate organization bootstrap lifecycle because the provider's `snowflake_account` resource requires organization-level privilege and initial administrator material.

## Database boundary

A database represents environment × data product, not physical source system.

For example, ten Health sources can still land under `DEV_HEALTH`/`UAT_HEALTH`/`PROD_HEALTH`, with source-purpose RAW schemas introduced when those sources are onboarded.

This gives a useful project storage/recovery boundary while compute/serverless cost attribution remains warehouse/query-tag/usage driven.

## Provider roles

Account stacks define:

```text
snowflake.sysadmin
snowflake.securityadmin
```

No credentials are stored in Terraform source. WIF/OIDC is the target CI/CD authentication mechanism.

## Local validation

```bash
terraform fmt -check -recursive terraform

for stack in dev uat prod; do
  terraform -chdir="terraform/stacks/${stack}" init -backend=false
  terraform -chdir="terraform/stacks/${stack}" validate
done
```

GitHub Actions performs the same credential-free validation matrix.

## Apply policy

Automated apply remains disabled until:

1. durable independent remote state is chosen for DEV/UAT/PROD;
2. GitHub workload identity federation is implemented/tested;
3. target account identifiers and execution roles are verified;
4. a DEV plan is reviewed/applied first;
5. Snowflake-side RBAC/object verification passes;
6. UAT is proven before any PROD path is enabled.

## What the baseline creates

### DEV account

- `DEV_HEALTH`, `CI_HEALTH`, `DEV_TRANSPORT`, `CI_TRANSPORT`;
- stable DEV transformation schemas; PR CI schemas stay ephemeral;
- Health/Transport DEV and CI warehouses;
- `WH_PLATFORM_OPS`;
- `PLATFORM_CONTROL` plus four structural schemas;
- platform/project account roles;
- only the owning project's `READ`/`WRITE`/`OWNER` database roles per database.

### UAT account

- `UAT_HEALTH`, `UAT_TRANSPORT`;
- stable transformation schemas;
- project UAT warehouses plus `WH_PLATFORM_OPS`;
- `PLATFORM_CONTROL`;
- UAT project developers read-only by default; admins hold the governed owner tier.

### PROD account

- `PROD_HEALTH`, `PROD_TRANSPORT`;
- stable transformation schemas;
- separate project transform/query warehouses plus `WH_PLATFORM_OPS`;
- `PLATFORM_CONTROL`;
- developer write disabled; project admins retain owner tier.

No ingestion pipelines, dbt models, Snowpipe Streaming, Kafka, Openflow, or speculative operational tables are created by this Terraform slice.
