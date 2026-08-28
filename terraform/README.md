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
    ├── nonprod/
    └── prod/
```

Environment object names and guardrail values come from:

```text
config/environments/nonprod.yml
config/environments/prod.yml
```

## Versions

```text
Terraform CLI:             1.16.0
Snowflake Terraform provider: 2.19.0
Provider source:           snowflakedb/snowflake
```

Root stacks pin exact versions. Module constraints permit the pinned 2.x baseline.

## Provider roles

Root stacks define two aliases:

```text
snowflake.sysadmin
snowflake.securityadmin
```

`SYSADMIN` is used for database/schema/warehouse lifecycle and database-scoped grants. `SECURITYADMIN` is used for account roles and grant hierarchy.

No credentials are stored in Terraform source.

## Local validation

From the repository root:

```bash
terraform fmt -check -recursive terraform

cd terraform/stacks/nonprod
terraform init -backend=false
terraform validate

cd ../prod
terraform init -backend=false
terraform validate
```

GitHub Actions performs the same credential-free checks.

## Planning against a Snowflake account

Do not add credentials to `.tfvars` or source files. Use a supported Snowflake provider authentication method/environment/config profile.

A plan against a real account is not yet part of CI because remote state and workload identity federation have not been established.

## Apply policy

Automated apply is intentionally disabled at this point.

Before the first shared NONPROD apply:

1. choose and document a durable remote Terraform state backend;
2. implement/test GitHub workload identity federation;
3. verify the executing roles can use `SYSADMIN`/`SECURITYADMIN` or replace them with tighter bootstrap roles;
4. generate and review a NONPROD plan;
5. apply NONPROD before enabling any PROD path.

## What this baseline creates

NONPROD:

- `ANALYTICS_DEV`, `ANALYTICS_CI`, `ANALYTICS_UAT`;
- project-qualified stable DEV/UAT schemas;
- Health/Transport DEV, CI and UAT warehouses;
- `WH_PLATFORM_OPS`;
- `PLATFORM_CONTROL` plus four structural schemas;
- platform/project account roles;
- per-database project `READ`/`WRITE`/`OWNER` database roles and baseline grants.

PROD:

- `ANALYTICS_PROD` plus project-qualified stable schemas;
- Health/Transport transform/query warehouses;
- `WH_PLATFORM_OPS`;
- `PLATFORM_CONTROL` plus four structural schemas;
- the same account/database role model with developer write disabled.

No ingestion pipelines, dbt models, Snowpipe Streaming, Kafka, Openflow, or operational control tables are created by this Terraform slice.
