-- Enterprise Snowflake pipeline quality/check result ledger.
--
-- GENERATION binds each technical check to the dataset lifecycle that produced it.
-- Historical generations remain available for audit after a full reset.

CREATE TABLE IF NOT EXISTS PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECK_RESULT (
    RUN_ID                  VARCHAR(128)     NOT NULL,
    ATTEMPT_NUMBER          NUMBER(38, 0)    NOT NULL DEFAULT 1,
    PROJECT_CODE            VARCHAR(64)      NOT NULL,
    ENVIRONMENT             VARCHAR(16)      NOT NULL,
    DATASET_ID              VARCHAR(64)      NOT NULL,
    GENERATION              NUMBER(38, 0)    NOT NULL DEFAULT 1,
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
COMMENT = 'Structured technical check outcomes versioned by dataset generation.';
