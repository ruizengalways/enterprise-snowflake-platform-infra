-- Runtime state for safe initial snapshot -> incremental/CDC handoff.
--
-- Lifecycle owner: platform-infra / PLATFORM_CONTROL.
-- Configuration remains in Git RAW contracts; this table stores only mutable
-- operational progress and captured source-boundary evidence.
--
-- Project roles must not receive direct DML on this base table. Domain-scoped
-- secure views and owner-rights procedures are generated separately.

CREATE TABLE IF NOT EXISTS PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP (
    PROJECT_CODE              VARCHAR(64)      NOT NULL,
    ENVIRONMENT               VARCHAR(16)      NOT NULL,
    DATASET_ID                VARCHAR(64)      NOT NULL,
    BOOTSTRAP_ID              VARCHAR(128)     NOT NULL,
    STATUS                    VARCHAR(32)      NOT NULL,
    HANDOFF_CHECKPOINT_KIND   VARCHAR(32)      NOT NULL,
    HANDOFF_POSITION          VARIANT          NOT NULL,
    INCREMENTAL_START         VARCHAR(64)      NOT NULL,
    SNAPSHOT_ID               VARCHAR(128),
    SNAPSHOT_BATCH_ID         VARCHAR(128),
    RECONCILIATION_PASSED     BOOLEAN,
    RECONCILIATION_DETAILS    VARIANT,
    GIT_SHA                   VARCHAR(64),
    BOUNDARY_CAPTURED_AT      TIMESTAMP_TZ     NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    SNAPSHOT_LANDED_AT        TIMESTAMP_TZ,
    SNAPSHOT_VALIDATED_AT     TIMESTAMP_TZ,
    HANDOFF_COMMITTED_AT      TIMESTAMP_TZ,
    ROW_VERSION               NUMBER(38, 0)    NOT NULL DEFAULT 1,
    UPDATED_AT                TIMESTAMP_TZ     NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_BY                VARCHAR(256)     NOT NULL DEFAULT CURRENT_USER(),
    CONSTRAINT PK_PIPELINE_BOOTSTRAP PRIMARY KEY (
        PROJECT_CODE,
        ENVIRONMENT,
        DATASET_ID,
        BOOTSTRAP_ID
    )
)
COMMENT = 'Mutable bootstrap handoff state. No business payloads or secrets.';
