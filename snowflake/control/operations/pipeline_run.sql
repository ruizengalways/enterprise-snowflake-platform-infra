-- Enterprise Snowflake pipeline execution ledger.
--
-- One row represents one execution attempt. GENERATION binds the run to the
-- dataset lifecycle in force when the run started; old generations remain audit.

CREATE TABLE IF NOT EXISTS PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN (
    RUN_ID                  VARCHAR(128)     NOT NULL,
    ATTEMPT_NUMBER          NUMBER(38, 0)    NOT NULL DEFAULT 1,
    PROJECT_CODE            VARCHAR(64)      NOT NULL,
    ENVIRONMENT             VARCHAR(16)      NOT NULL,
    PIPELINE_ID             VARCHAR(128)     NOT NULL,
    DATASET_ID              VARCHAR(64),
    GENERATION              NUMBER(38, 0)    NOT NULL DEFAULT 1,
    STATUS                  VARCHAR(16)      NOT NULL,
    STARTED_AT              TIMESTAMP_TZ     NOT NULL,
    FINISHED_AT             TIMESTAMP_TZ,
    GIT_SHA                 VARCHAR(64),
    QUERY_TAG               VARIANT,
    CHECKPOINT_BEFORE       VARIANT,
    CHECKPOINT_AFTER        VARIANT,
    ROWS_READ               NUMBER(38, 0),
    ROWS_WRITTEN            NUMBER(38, 0),
    ROWS_INSERTED           NUMBER(38, 0),
    ROWS_UPDATED            NUMBER(38, 0),
    ROWS_DELETED            NUMBER(38, 0),
    ERROR_CLASS             VARCHAR(256),
    ERROR_MESSAGE           VARCHAR(8192),
    DETAILS                 VARIANT,
    CREATED_AT              TIMESTAMP_TZ     NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT              TIMESTAMP_TZ     NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_BY              VARCHAR(256)     NOT NULL DEFAULT CURRENT_USER(),
    CONSTRAINT PK_PIPELINE_RUN PRIMARY KEY (RUN_ID, ATTEMPT_NUMBER)
)
COMMENT = 'Pipeline execution attempts versioned by dataset generation; never business payloads.';
