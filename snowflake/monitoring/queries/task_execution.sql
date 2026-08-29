-- Snowflake-native Task execution diagnostics.
--
-- Task-driven pipelines use Snowflake TASK_HISTORY as the authoritative run
-- ledger. Do not mirror every Task run into PLATFORM_CONTROL.PIPELINE_RUN.

-- Recent Task executions, including triggered/manual/automatic retry origin.
SELECT
    DATABASE_NAME,
    SCHEMA_NAME,
    NAME AS TASK_NAME,
    GRAPH_RUN_GROUP_ID,
    ATTEMPT_NUMBER,
    SCHEDULED_FROM,
    STATE,
    SCHEDULED_TIME,
    QUERY_START_TIME,
    COMPLETED_TIME,
    QUERY_ID,
    ERROR_CODE,
    ERROR_MESSAGE,
    RETURN_VALUE
FROM SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY
WHERE SCHEDULED_TIME >= DATEADD('DAY', -1, CURRENT_TIMESTAMP())
ORDER BY SCHEDULED_TIME DESC;

-- Failures/cancellations only. This is intended for operational triage and
-- alert-source queries; native Task ERROR_INTEGRATION can be configured when
-- immediate notification delivery is required.
SELECT
    DATABASE_NAME,
    SCHEMA_NAME,
    NAME AS TASK_NAME,
    GRAPH_RUN_GROUP_ID,
    ATTEMPT_NUMBER,
    SCHEDULED_FROM,
    STATE,
    QUERY_START_TIME,
    COMPLETED_TIME,
    ERROR_CODE,
    ERROR_MESSAGE
FROM SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY
WHERE SCHEDULED_TIME >= DATEADD('DAY', -7, CURRENT_TIMESTAMP())
  AND STATE IN ('FAILED', 'CANCELLED')
ORDER BY SCHEDULED_TIME DESC;
