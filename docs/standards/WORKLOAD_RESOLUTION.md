# Logical Workload to Warehouse Resolution

Domain dataset metadata names a logical workload, not a physical warehouse:

```yaml
compute:
  workload: transform
```

The platform owns the physical mapping:

```text
(domain, environment, workload) -> warehouse
```

Environment configuration already implements this through each project's `warehouse_keys` and the environment `warehouses` map. For example, in the DEV account:

```text
TRANSPORT + transform -> transport_transform -> WH_TRANSPORT_TRANSFORM
HEALTH    + transform -> health_transform    -> WH_HEALTH_TRANSFORM
```

The Snowflake account already conveys the environment, so physical warehouse names need not repeat `DEV`, `UAT` or `PROD` unless an environment has a deliberate naming exception.

## Rules

- Dataset metadata must not hard-code physical warehouse names.
- Platform config may tune size, suspend timeout or replace a physical warehouse without changing every dataset config.
- `query`, `transform`, `ci` and platform-only workloads are platform concepts; add a new workload only when it represents a durable compute/security/cost boundary.
- Workload resolution is environment/platform configuration, not domain business logic.
- Cost attribution continues to use domain/workload query tags in addition to warehouse-level attribution.
