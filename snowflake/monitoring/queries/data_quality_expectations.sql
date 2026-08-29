-- Snowflake-native Data Quality Monitoring diagnostics.
-- Requires Snowflake Enterprise Edition and the appropriate Snowflake
-- application-role/object privileges.
--
-- System DMFs + EXPECTATION are the preferred baseline for supported standard
-- checks. Cross-table/cross-system reconciliation remains explicit SQL.

-- Current expectation status across visible monitored objects.
SELECT
    REF_DATABASE_NAME,
    REF_SCHEMA_NAME,
    REF_ENTITY_NAME,
    REF_ENTITY_DOMAIN,
    METRIC_DATABASE_NAME,
    METRIC_SCHEMA_NAME,
    METRIC_NAME,
    EXPECTATION_NAME,
    EXPECTATION_EXPRESSION,
    VALUE AS EXPECTATION_VIOLATED,
    SCHEDULED_TIME,
    MEASUREMENT_TIME,
    CHANGE_COMMIT_TIME
FROM SNOWFLAKE.LOCAL.DATA_QUALITY_MONITORING_EXPECTATION_STATUS
ORDER BY SCHEDULED_TIME DESC, REF_DATABASE_NAME, REF_SCHEMA_NAME, REF_ENTITY_NAME;

-- Declarative associations/expectations configured in the account.
SELECT
    METRIC_DATABASE_NAME,
    METRIC_SCHEMA_NAME,
    METRIC_NAME,
    REF_DATABASE_NAME,
    REF_SCHEMA_NAME,
    REF_ENTITY_NAME,
    REF_ENTITY_DOMAIN,
    EXPECTATION_NAME,
    EXPECTATION_EXPRESSION
FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_METRIC_FUNCTION_EXPECTATIONS
ORDER BY REF_DATABASE_NAME, REF_SCHEMA_NAME, REF_ENTITY_NAME, METRIC_NAME;
