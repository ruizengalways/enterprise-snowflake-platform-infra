# ADR-006 — Metadata-driven technical behaviour

- **Status:** Accepted
- **Date:** 2026-08-28

## Context

New data projects should be able to onboard common table patterns quickly without reimplementing composite-key handling, watermarks, deduplication, MERGE mechanics, SCD2 mechanics, audit metadata, freshness, reconciliation and standard tests. At the same time, business logic differs legitimately between domains and should remain readable code.

## Decision

Use metadata for stable, repetitive technical behaviour and explicit SQL/code for genuine business logic.

Metadata may configure strategy, keys, timestamps, tracked columns, delete behaviour, deduplication policy, freshness thresholds, reconciliation, criticality and standard quality policies.

The framework must not evolve into a general-purpose YAML programming language for arbitrary transformations, joins or calculations.

Support:

```yaml
implementation: custom
```

Custom implementations remain subject to standard contracts, testing, observability, reconciliation, audit and recovery requirements.

## Consequences

- Common engineering behaviour can be fixed once in the framework and upgraded by projects through versioned dependencies.
- Project repositories remain readable because domain rules stay in SQL/code.
- Metadata schemas need validation and versioning.
- Framework authors must resist adding configuration knobs for one-off business rules.