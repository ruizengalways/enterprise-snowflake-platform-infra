# ADR-031 — Ingestion Independence and Bronze Contract

- **Status:** Replaced — 2026-09-09

## Decision

The platform boundary is explicit:

```text
Source -> Bronze = ingestion responsibility
Bronze -> Silver -> Gold = data processing responsibility
```

The shared data-processing Framework is connector-agnostic. Openflow, Snowpipe, Kafka, Fivetran, Airbyte, ADF, custom Python/JDBC and synthetic simulators can all provide the same Bronze/source contract.

Source contracts describe source semantics and evidence fidelity: grain, business key, source timestamp, CDC operation, sequence, delete semantics and idempotency requirements. They may document source capture fidelity, but they do not make the processing Framework responsible for operating the connector.

Connector-owned positions such as SQL Server LSNs, Kafka source offsets, API cursors or ingestion-tool checkpoints are not Framework checkpoints. Framework runtime state begins after data is landed in Snowflake. Processing checkpoints may track landed-data boundaries such as a watermark, event offset, snapshot identity or file identity where useful.

## Dynamic Tables

Dynamic Tables are a materialization/runtime capability, not a load strategy and not an ingestion mechanism.

Golden path:

```text
Silver -> correctness / state / authoritative history
Gold   -> declarative business derivation
```

Dynamic Tables are Gold-first. They can be used elsewhere with a clear reason, but complex stateful SCD2 history is not maintained by Dynamic Table by default. Gold Dynamic Tables should prefer `REFRESH_MODE = ADAPTIVE` when appropriate.

## Portability

Standalone synthetic domain cores remain independent of Framework, PLATFORM_CONTROL, Terraform and enterprise workload identity. Enterprise wrappers may be added around that portable core without making the core depend on platform infrastructure.
