# ADR-007 — RAW contract as ingestion/downstream boundary

- **Status:** Accepted
- **Date:** 2026-08-28

## Context

The platform must support multiple ingestion implementations without forcing downstream dbt models to be redesigned. Health and Transport will intentionally exercise different ingestion patterns, including synthetic sources, Snowpipe Streaming, Kafka Connector and later Openflow CDC.

## Decision

Treat the project-owned RAW contract as the stable boundary between ingestion and downstream Snowflake data engineering.

All ingestion mechanisms must converge on the same logical RAW contract for a dataset. The contract defines grain, keys, required columns/types, source timestamps, operation semantics, ordering/sequence metadata where applicable, cadence, retention, classification and schema-evolution policy.

Downstream staging/canonical/marts must depend on the RAW contract rather than the ingestion technology.

## Consequences

- Direct Snowpipe Streaming and Kafka Connector can be compared using the same Transport event dataset and downstream pipeline.
- Openflow can be added to Health later without an architectural redesign of downstream models.
- Contract compatibility becomes a CI concern.
- Ingestion adapters may need technology-specific mapping code, but that mapping stops at RAW.