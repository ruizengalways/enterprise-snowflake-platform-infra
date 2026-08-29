# Cost Attribution Standard

## Purpose

Define a practical multi-dimensional cost-attribution model for the Enterprise Snowflake Platform without using database-per-source or pretending that one Snowflake history view is the full bill.

## Principle

Different Snowflake boundaries answer different cost questions:

```text
Domain storage / recovery        -> <ENVIRONMENT>_<DOMAIN> database
Compute                          -> WH_<DOMAIN>_<WORKLOAD>
Per-query execution attribution  -> QUERY_TAG + QUERY_ATTRIBUTION_HISTORY
Warehouse idle compute           -> WAREHOUSE_METERING_HISTORY
Serverless / ingestion services  -> service-specific ACCOUNT_USAGE histories
Fine storage detail              -> table/schema/database storage histories
```

Do not create a database per physical source merely for chargeback.

## Warehouse boundary

Canonical warehouses are:

```text
WH_<DOMAIN>_QUERY
WH_<DOMAIN>_TRANSFORM
WH_<DOMAIN>_CI   # DEV account only
WH_PLATFORM_OPS
```

The warehouse is the primary compute/cost isolation boundary. The account identifies DEV/UAT/PROD; the warehouse identifies domain + workload.

## Query-tag contract

Framework-driven workloads use compact JSON in Snowflake `QUERY_TAG`.

Required fields:

```text
project
environment
workload
```

Optional standard fields:

```text
source
pipeline
dataset
run_id
git_sha
pr_number
operation
```

Example:

```json
{"dataset":"patient","environment":"prod","git_sha":"abc123","pipeline":"patient_publish","project":"health","run_id":"9911","workload":"transform"}
```

The shared builder lives in `enterprise-snowflake-data-project-framework` and rejects unsupported keys and tags above Snowflake's 2000-character limit.

Do not put personal data, secrets, patient/customer identifiers, regulated values, free-form SQL, or business payload data in query tags. Query tags are operational metadata.

## Attribution rules

### Query compute

Use `SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY` for standard-warehouse query execution attribution. It exposes `QUERY_TAG` and `CREDITS_ATTRIBUTED_COMPUTE`.

This metric excludes warehouse idle time. Therefore:

```text
query-attributed compute != complete warehouse compute bill
```

### Warehouse compute and idle

Use `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY` for total warehouse usage.

A useful operational measure is:

```text
idle_compute_credits
  = credits_used_compute
  - credits_attributed_compute_queries
```

This helps distinguish expensive SQL from warehouses that simply remain running while idle.

### Serverless / ingestion

Do not force serverless costs into warehouse attribution. Snowpipe, Snowpipe Streaming, automatic clustering, serverless tasks and later platform services use their relevant Snowflake usage histories.

### Storage

Database naming provides the domain/environment storage boundary. Use lower-level storage metrics when source/table detail is required rather than splitting every physical source into its own database.

## Query templates

The source-controlled baseline queries live at:

```text
snowflake/monitoring/queries/cost_attribution.sql
```

They are diagnostic queries, not persisted views yet. Persisted `PLATFORM_CONTROL.OBSERVABILITY` views should be introduced only after the live account access/ownership model is proven.

## Access model

Do not grant ACCOUNTADMIN to analysts merely to read cost history. When live Snowflake accounts are available, create the narrowest platform observability/cost-reader access that can query the required `SNOWFLAKE.ACCOUNT_USAGE` objects.

That privilege is not added speculatively in static Terraform because the real account/provider access path still needs live verification.

## Reconciliation

Cost reporting should preserve the distinction between:

```text
query attribution
warehouse metering
serverless service usage
storage usage
billed daily usage
```

A dashboard may combine them, but it must not silently label partial query attribution as the exact Snowflake invoice.
