-- Advance one governed capture checkpoint after successful target processing.
--
-- Call this only after the corresponding batch/change DML succeeds. When the
-- caller needs atomic target-DML + checkpoint advancement, invoke the CALL in
-- the same explicit transaction / Snowflake Scripting block as the target DML.
--
-- Runtime invariant: one logical writer per (project, dataset, checkpoint_kind).

CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.OPERATIONS.ADVANCE_PIPELINE_CHECKPOINT(
    P_PROJECT_CODE VARCHAR,
    P_DATASET_ID VARCHAR,
    P_CHECKPOINT_KIND VARCHAR,
    P_CHECKPOINT_VALUE VARIANT,
    P_BATCH_ID VARCHAR,
    P_GIT_SHA VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
BEGIN
    MERGE INTO PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT AS target
    USING (
        SELECT
            UPPER(TRIM(:P_PROJECT_CODE)) AS PROJECT_CODE,
            LOWER(TRIM(:P_DATASET_ID)) AS DATASET_ID,
            LOWER(TRIM(:P_CHECKPOINT_KIND)) AS CHECKPOINT_KIND,
            :P_CHECKPOINT_VALUE AS CHECKPOINT_VALUE,
            :P_BATCH_ID AS LAST_SUCCESSFUL_BATCH_ID,
            :P_GIT_SHA AS LAST_GIT_SHA
    ) AS source
      ON target.PROJECT_CODE = source.PROJECT_CODE
     AND target.DATASET_ID = source.DATASET_ID
     AND target.CHECKPOINT_KIND = source.CHECKPOINT_KIND
    WHEN MATCHED THEN UPDATE SET
        CHECKPOINT_VALUE = source.CHECKPOINT_VALUE,
        LAST_SUCCESSFUL_BATCH_ID = source.LAST_SUCCESSFUL_BATCH_ID,
        LAST_SUCCESSFUL_AT = CURRENT_TIMESTAMP(),
        LAST_GIT_SHA = source.LAST_GIT_SHA,
        ROW_VERSION = target.ROW_VERSION + 1,
        UPDATED_AT = CURRENT_TIMESTAMP(),
        UPDATED_BY = CURRENT_USER()
    WHEN NOT MATCHED THEN INSERT (
        PROJECT_CODE,
        DATASET_ID,
        CHECKPOINT_KIND,
        CHECKPOINT_VALUE,
        LAST_SUCCESSFUL_BATCH_ID,
        LAST_SUCCESSFUL_AT,
        LAST_GIT_SHA,
        ROW_VERSION,
        UPDATED_AT,
        UPDATED_BY
    ) VALUES (
        source.PROJECT_CODE,
        source.DATASET_ID,
        source.CHECKPOINT_KIND,
        source.CHECKPOINT_VALUE,
        source.LAST_SUCCESSFUL_BATCH_ID,
        CURRENT_TIMESTAMP(),
        source.LAST_GIT_SHA,
        1,
        CURRENT_TIMESTAMP(),
        CURRENT_USER()
    );

    RETURN 'checkpoint advanced';
END;
$$;
