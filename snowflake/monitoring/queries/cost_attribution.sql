-- Enterprise Snowflake Platform cost-attribution baseline.
--
-- These are bounded diagnostic queries, not persisted objects. Access to
-- SNOWFLAKE.ACCOUNT_USAGE is granted separately to an approved platform
-- observability/cost role when the live account is available.
--
-- QUERY_ATTRIBUTION_HISTORY attributes compute to query execution and excludes
-- warehouse idle time. WAREHOUSE_METERING_HISTORY is used separately to measure
-- total warehouse compute and idle credits.

-- 1. Tagged query compute by project/workload/dataset for the last 7 days.
WITH tagged_queries AS (
    SELECT
        query_id,
        warehouse_name,
        user_name,
        start_time,
        end_time,
        credits_attributed_compute,
        COALESCE(credits_used_query_acceleration, 0) AS credits_used_query_acceleration,
        TRY_PARSE_JSON(query_tag) AS tag
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY
    WHERE start_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
      AND query_tag IS NOT NULL
)
SELECT
    tag:project::STRING AS project,
    tag:environment::STRING AS environment,
    tag:workload::STRING AS workload,
    tag:source::STRING AS source,
    tag:pipeline::STRING AS pipeline,
    tag:dataset::STRING AS dataset,
    warehouse_name,
    COUNT(*) AS query_count,
    SUM(credits_attributed_compute) AS query_compute_credits,
    SUM(credits_used_query_acceleration) AS query_acceleration_credits
FROM tagged_queries
WHERE tag IS NOT NULL
GROUP BY ALL
ORDER BY query_compute_credits DESC;

-- 2. Warehouse compute versus query-attributed compute and idle credits.
SELECT
    warehouse_name,
    SUM(credits_used_compute) AS warehouse_compute_credits,
    SUM(COALESCE(credits_attributed_compute_queries, 0)) AS query_attributed_compute_credits,
    SUM(credits_used_compute) - SUM(COALESCE(credits_attributed_compute_queries, 0)) AS idle_compute_credits,
    CASE
        WHEN SUM(credits_used_compute) = 0 THEN 0
        ELSE (
            SUM(credits_used_compute) - SUM(COALESCE(credits_attributed_compute_queries, 0))
        ) / SUM(credits_used_compute)
    END AS idle_compute_ratio
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE start_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY warehouse_name
ORDER BY warehouse_compute_credits DESC;

-- 3. Domain/workload warehouse rollup. Naming is itself a cost boundary.
SELECT
    warehouse_name,
    SUM(credits_used) AS credits_used,
    SUM(credits_used_compute) AS credits_used_compute,
    SUM(credits_used_cloud_services) AS credits_used_cloud_services,
    SUM(COALESCE(credits_attributed_compute_queries, 0)) AS credits_attributed_compute_queries
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE start_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
  AND (
      warehouse_name LIKE 'WH\_%\_QUERY' ESCAPE '\\'
      OR warehouse_name LIKE 'WH\_%\_TRANSFORM' ESCAPE '\\'
      OR warehouse_name LIKE 'WH\_%\_CI' ESCAPE '\\'
      OR warehouse_name = 'WH_PLATFORM_OPS'
  )
GROUP BY warehouse_name
ORDER BY credits_used DESC;
