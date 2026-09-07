-- Current dataset lifecycle/generation state.
--
-- A reset abandons the current generation and advances CURRENT_GENERATION.
-- Historical runtime rows remain auditable under their old GENERATION while
-- current-state views/procedures resolve only the generation stored here.

CREATE TABLE IF NOT EXISTS PLATFORM_CONTROL.OPERATIONS.DATASET_LIFECYCLE (
    PROJECT_CODE          VARCHAR(64)      NOT NULL,
    ENVIRONMENT           VARCHAR(16)      NOT NULL,
    DATASET_ID            VARCHAR(64)      NOT NULL,
    CURRENT_GENERATION    NUMBER(38, 0)    NOT NULL DEFAULT 1,
    STATE                 VARCHAR(32)      NOT NULL DEFAULT 'ACTIVE',
    LAST_RESET_ID         VARCHAR(128),
    ROW_VERSION           NUMBER(38, 0)    NOT NULL DEFAULT 1,
    CREATED_AT            TIMESTAMP_TZ     NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT            TIMESTAMP_TZ     NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_BY            VARCHAR(256)     NOT NULL DEFAULT CURRENT_USER(),
    CONSTRAINT PK_DATASET_LIFECYCLE PRIMARY KEY (
        PROJECT_CODE,
        ENVIRONMENT,
        DATASET_ID
    )
)
COMMENT = 'Current dataset generation and reset lifecycle state; configuration remains in Git.';
