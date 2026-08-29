-- Enterprise Snowflake runtime checkpoint state.
--
-- Lifecycle owner: platform-infra / PLATFORM_CONTROL.
-- Configuration remains in Git; only mutable execution progress belongs here.
--
-- Apply after PLATFORM_CONTROL.OPERATIONS exists. The object is intentionally
-- generic across watermark, cursor, source-position, event-offset, snapshot and
-- file-identity capture patterns.

CREATE TABLE IF NOT EXISTS PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT (
    PROJECT_CODE              VARCHAR(64)      NOT NULL,
    DATASET_ID                VARCHAR(64)      NOT NULL,
    CHECKPOINT_KIND           VARCHAR(32)      NOT NULL,
    CHECKPOINT_VALUE          VARIANT,
    LAST_SUCCESSFUL_BATCH_ID  VARCHAR(128),
    LAST_SUCCESSFUL_AT        TIMESTAMP_TZ,
    LAST_GIT_SHA              VARCHAR(64),
    ROW_VERSION               NUMBER(38, 0)    NOT NULL DEFAULT 0,
    UPDATED_AT                TIMESTAMP_TZ     NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_BY                VARCHAR(256)     NOT NULL DEFAULT CURRENT_USER(),
    CONSTRAINT PK_PIPELINE_CHECKPOINT PRIMARY KEY (PROJECT_CODE, DATASET_ID, CHECKPOINT_KIND)
)
COMMENT = 'Mutable source-capture checkpoint state. Do not store business payloads or secrets.';
