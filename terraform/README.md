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
    ├── organization/
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

## Versions

```text
Terraform CLI:                  1.16.0
Snowflake Terraform provider:   2.19.0
Provider source:                snowflakedb/snowflake
```

## Organization bootstrap

`terraform/stacks/organization` is the only root that uses `ORGADMIN`. It creates or imports the three environment accounts:

```text
DEV
UAT
PROD
```

The initial account admin is a bootstrap-only `SERVICE` user with an RSA public key supplied outside Git. Account resources use `prevent_destroy = true`.

Normal DEV/UAT/PROD roots never use ORGADMIN.

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

A database represents environment × data product/domain, not physical source system. Ten Health sources can still land under the Health project database, with source-purpose RAW schemas introduced when those sources are actually onboarded.

## Domain RBAC

Every domain receives an independent account-role hierarchy:

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

Account already identifies environment, so warehouse naming focuses on domain + workload:

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

GUEST receives the domain QUERY warehouse. DEV DEVELOPER additionally receives TRANSFORM. UAT/PROD ADMIN currently receives TRANSFORM until deployment workload identity takes over. CI warehouses are reserved for machine identities.

This gives useful compute cost attribution without creating database-per-source.

## Provider roles

Account stacks define:

```text
snowflake.sysadmin
snowflake.securityadmin
```

Organization bootstrap defines:

```text
snowflake.orgadmin
```

No credentials or private keys are stored in Terraform source. WIF/OIDC is the target routine CI/CD authentication mechanism.

## Local validation

```bash
terraform fmt -check -recursive terraform

for stack in organization dev uat prod; do
  terraform -chdir="terraform/stacks/${stack}" init -backend=false
  terraform -chdir="terraform/stacks/${stack}" validate
done
```

GitHub Actions is configured for the same credential-free validation matrix.

## Apply policy

Automated apply remains disabled until:

1. durable independent remote state is chosen for organization/DEV/UAT/PROD;
2. organization bootstrap credentials are handled through a controlled one-time process;
3. GitHub workload identity federation is implemented/tested for routine account stacks;
4. target account identifiers and execution roles are verified;
5. a DEV plan is reviewed/applied first;
6. Snowflake-side RBAC/object verification passes;
7. UAT is proven before any PROD path is enabled.

## What the baseline creates

### Organization bootstrap

- DEV/UAT/PROD accounts from `config/organization.yml`;
- Enterprise edition baseline;
- bootstrap SERVICE administrator using external RSA public-key input;
- protected account lifecycle with `prevent_destroy`.

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
- developers read-only by default; admins retain the governed owner/transform tier until machine deployment exists.

### PROD account

- `PROD_HEALTH`, `PROD_TRANSPORT`;
- stable transformation schemas;
- domain query/transform warehouses plus `WH_PLATFORM_OPS`;
- published-layer GUEST access;
- developer write disabled; domain admins retain owner/transform tier until machine deployment exists.

No ingestion pipelines, dbt models, Snowpipe Streaming, Kafka, Openflow, or speculative operational tables are created by this Terraform slice.
