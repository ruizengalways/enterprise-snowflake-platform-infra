-- Auditable full-reset ledger.
--
-- RESET is intentionally separate from repair/replay. Reset means abandon the
-- current dataset generation, clear reconstructable domain data, and restart
-- from source with no current-generation checkpoint/bootstrap state.

CREATE TABLE IF NOT EXISTS PLATFORM_CONTROL.OPERATIONS.DATASET_RESET (
    RESET_ID            VARCHAR(128)     NOT NULL,
    PROJECT_CODE        VARCHAR(64)      NOT NULL,
    ENVIRONMENT         VARCHAR(16)      NOT NULL,
    DATASET_ID          VARCHAR(64)      NOT NULL,
    FROM_GENERATION     NUMBER(38, 0)    NOT NULL,
    TO_GENERATION       NUMBER(38, 0)    NOT NULL,
    STATUS              VARCHAR(32)      NOT NULL,
    REASON              VARCHAR(2048)    NOT NULL,
    GIT_SHA             VARCHAR(64),
    DETAILS             VARIANT,
    REQUESTED_AT        TIMESTAMP_TZ     NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    REQUESTED_BY        VARCHAR(256)     NOT NULL DEFAULT CURRENT_USER(),
    RESET_STARTED_AT    TIMESTAMP_TZ,
    READY_FOR_RELOAD_AT TIMESTAMP_TZ,
    COMPLETED_AT        TIMESTAMP_TZ,
    UPDATED_AT          TIMESTAMP_TZ     NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_BY          VARCHAR(256)     NOT NULL DEFAULT CURRENT_USER(),
    CONSTRAINT PK_DATASET_RESET PRIMARY KEY (RESET_ID)
)
COMMENT = 'Full dataset reset audit ledger. Repair/replay is a separate recovery concern.';
