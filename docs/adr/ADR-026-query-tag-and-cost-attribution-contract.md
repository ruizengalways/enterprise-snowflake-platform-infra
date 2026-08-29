# ADR-026 — Query-tag and cost-attribution contract

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

The platform needs cost attribution below account level without creating one Snowflake database per physical source or pretending one usage view is the exact invoice.

Warehouse isolation already provides a domain/workload compute boundary. More detailed attribution requires stable query metadata, while idle warehouse compute and serverless services must remain separately visible.

## Decision

Adopt a compact JSON Snowflake `QUERY_TAG` contract for framework-driven SQL.

Required keys:

```text
project
environment
workload
```

Optional standard keys:

```text
source
pipeline
dataset
run_id
git_sha
pr_number
operation
```

The shared builder lives in `enterprise-snowflake-data-project-framework`, validates the vocabulary, renders deterministic compact JSON, and fails before Snowflake's 2000-character query-tag limit.

Operational metadata must not contain personal data, secrets, regulated identifiers, business payloads or free-form SQL.

## Cost model

Use complementary sources:

```text
Domain/environment storage     -> <ENVIRONMENT>_<DOMAIN> databases
Domain/workload compute        -> WH_<DOMAIN>_<WORKLOAD>
Per-query standard-WH compute  -> QUERY_ATTRIBUTION_HISTORY + QUERY_TAG
Warehouse idle compute         -> WAREHOUSE_METERING_HISTORY
Serverless/ingestion           -> service-specific usage histories
Fine storage detail            -> Snowflake storage metrics/history
```

`CREDITS_ATTRIBUTED_COMPUTE` excludes warehouse idle time, so query attribution must not be labelled as total warehouse cost.

The baseline diagnostic SQL is source-controlled at:

```text
snowflake/monitoring/queries/cost_attribution.sql
```

Persisted cost views/tables are deferred until live-account access and lifecycle ownership are proven.

## Consequences

- Query tags become part of the shared technical delivery contract.
- Warehouse naming remains the primary compute isolation boundary.
- Cost reporting can drill into project/source/pipeline/dataset/run without database-per-source.
- Idle warehouse cost remains visible rather than being silently spread across queries.
- Serverless ingestion/processing is accounted for separately.
- Exact invoice reconciliation remains a distinct concern from operational attribution.
