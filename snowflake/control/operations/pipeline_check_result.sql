-- Enterprise Snowflake pipeline quality/check result ledger.
--
-- Lifecycle owner: platform-infra / PLATFORM_CONTROL.
-- Freshness, reconciliation and other technical checks write structured results
-- here. Business payloads and regulated values must not be persisted in DETAILS.

CREATE TABLE IF NOT EXISTS PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECK_RESULT (
    RUN_ID                  VARCHAR(128)     NOT NULL,
    ATTEMPT_NUMBER          NUMBER(38, 0)    NOT NULL DEFAULT 1,
    PROJECT_CODE            VARCHAR(64)      NOT NULL,
    ENVIRONMENT             VARCHAR(16)      NOT NULL,
    DATASET_ID              VARCHAR(64)      NOT NULL,
    CHECK_TYPE              VARCHAR(32)      NOT NULL,
    CHECK_NAME              VARCHAR(128)     NOT NULL,
    STATUS                  VARCHAR(16)      NOT NULL,
    MEASURE_NAME            VARCHAR(128),
    OBSERVED_VALUE          VARIANT,
    EXPECTED_VALUE          VARIANT,
    DETAILS                 VARIANT,
    CHECKED_AT              TIMESTAMP_TZ     NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    RECORDED_BY             VARCHAR(256)     NOT NULL DEFAULT CURRENT_USER()
)
COMMENT = 'Structured technical freshness/reconciliation/check outcomes linked to pipeline runs.';
