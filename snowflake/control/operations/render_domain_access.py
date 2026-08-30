#!/usr/bin/env python3
"""Render domain-scoped PLATFORM_CONTROL access SQL from environment metadata."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

_IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9_]{0,62}[A-Z0-9]$|^[A-Z]$")
_ALLOWED_ENVIRONMENTS = {"DEV", "UAT", "PROD"}


def _identifier(value: object, field: str) -> str:
    text = str(value or "").strip().upper()
    if not _IDENTIFIER.fullmatch(text):
        raise ValueError(f"{field} must be an unquoted Snowflake-safe identifier, got {value!r}")
    return text


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _view_sql(code: str, base_name: str) -> str:
    view_name = f"{code}_{base_name}"
    return f"""CREATE OR REPLACE SECURE VIEW PLATFORM_CONTROL.OPERATIONS.{view_name} AS
SELECT *
FROM PLATFORM_CONTROL.OPERATIONS.{base_name}
WHERE PROJECT_CODE = {_sql_literal(code)};
"""


def _checkpoint_procedure(code: str) -> str:
    name = f"{code}_ADVANCE_PIPELINE_CHECKPOINT"
    return f"""CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.OPERATIONS.{name}(
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
            {_sql_literal(code)} AS PROJECT_CODE,
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
"""


def _run_start_procedure(code: str, environment: str) -> str:
    name = f"{code}_PIPELINE_RUN_START"
    return f"""CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.OPERATIONS.{name}(
    P_RUN_ID VARCHAR,
    P_ATTEMPT_NUMBER NUMBER,
    P_PIPELINE_ID VARCHAR,
    P_DATASET_ID VARCHAR,
    P_GIT_SHA VARCHAR,
    P_QUERY_TAG VARIANT,
    P_CHECKPOINT_BEFORE VARIANT
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
BEGIN
    MERGE INTO PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN AS target
    USING (
        SELECT
            :P_RUN_ID AS RUN_ID,
            :P_ATTEMPT_NUMBER AS ATTEMPT_NUMBER,
            {_sql_literal(code)} AS PROJECT_CODE,
            {_sql_literal(environment)} AS ENVIRONMENT,
            :P_PIPELINE_ID AS PIPELINE_ID,
            :P_DATASET_ID AS DATASET_ID,
            :P_GIT_SHA AS GIT_SHA,
            :P_QUERY_TAG AS QUERY_TAG,
            :P_CHECKPOINT_BEFORE AS CHECKPOINT_BEFORE
    ) AS source
      ON target.RUN_ID = source.RUN_ID
     AND target.ATTEMPT_NUMBER = source.ATTEMPT_NUMBER
     AND target.PROJECT_CODE = source.PROJECT_CODE
     AND target.ENVIRONMENT = source.ENVIRONMENT
    WHEN MATCHED THEN UPDATE SET
        PIPELINE_ID = source.PIPELINE_ID,
        DATASET_ID = source.DATASET_ID,
        STATUS = 'RUNNING',
        STARTED_AT = CURRENT_TIMESTAMP(),
        FINISHED_AT = NULL,
        GIT_SHA = source.GIT_SHA,
        QUERY_TAG = source.QUERY_TAG,
        CHECKPOINT_BEFORE = source.CHECKPOINT_BEFORE,
        CHECKPOINT_AFTER = NULL,
        ERROR_CLASS = NULL,
        ERROR_MESSAGE = NULL,
        UPDATED_AT = CURRENT_TIMESTAMP(),
        UPDATED_BY = CURRENT_USER()
    WHEN NOT MATCHED THEN INSERT (
        RUN_ID,
        ATTEMPT_NUMBER,
        PROJECT_CODE,
        ENVIRONMENT,
        PIPELINE_ID,
        DATASET_ID,
        STATUS,
        STARTED_AT,
        GIT_SHA,
        QUERY_TAG,
        CHECKPOINT_BEFORE
    ) VALUES (
        source.RUN_ID,
        source.ATTEMPT_NUMBER,
        source.PROJECT_CODE,
        source.ENVIRONMENT,
        source.PIPELINE_ID,
        source.DATASET_ID,
        'RUNNING',
        CURRENT_TIMESTAMP(),
        source.GIT_SHA,
        source.QUERY_TAG,
        source.CHECKPOINT_BEFORE
    );

    RETURN 'pipeline run started';
END;
$$;
"""


def _run_finish_procedure(code: str, environment: str) -> str:
    name = f"{code}_PIPELINE_RUN_FINISH"
    return f"""CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.OPERATIONS.{name}(
    P_RUN_ID VARCHAR,
    P_ATTEMPT_NUMBER NUMBER,
    P_STATUS VARCHAR,
    P_CHECKPOINT_AFTER VARIANT,
    P_ROWS_READ NUMBER,
    P_ROWS_WRITTEN NUMBER,
    P_ROWS_INSERTED NUMBER,
    P_ROWS_UPDATED NUMBER,
    P_ROWS_DELETED NUMBER,
    P_ERROR_CLASS VARCHAR,
    P_ERROR_MESSAGE VARCHAR,
    P_DETAILS VARIANT
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
BEGIN
    UPDATE PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN
    SET
        STATUS = UPPER(TRIM(:P_STATUS)),
        FINISHED_AT = CURRENT_TIMESTAMP(),
        CHECKPOINT_AFTER = :P_CHECKPOINT_AFTER,
        ROWS_READ = :P_ROWS_READ,
        ROWS_WRITTEN = :P_ROWS_WRITTEN,
        ROWS_INSERTED = :P_ROWS_INSERTED,
        ROWS_UPDATED = :P_ROWS_UPDATED,
        ROWS_DELETED = :P_ROWS_DELETED,
        ERROR_CLASS = :P_ERROR_CLASS,
        ERROR_MESSAGE = :P_ERROR_MESSAGE,
        DETAILS = :P_DETAILS,
        UPDATED_AT = CURRENT_TIMESTAMP(),
        UPDATED_BY = CURRENT_USER()
    WHERE RUN_ID = :P_RUN_ID
      AND ATTEMPT_NUMBER = :P_ATTEMPT_NUMBER
      AND PROJECT_CODE = {_sql_literal(code)}
      AND ENVIRONMENT = {_sql_literal(environment)};

    RETURN 'pipeline run finished';
END;
$$;
"""


def _check_result_procedure(code: str, environment: str) -> str:
    name = f"{code}_RECORD_PIPELINE_CHECK_RESULT"
    return f"""CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.OPERATIONS.{name}(
    P_RUN_ID VARCHAR,
    P_ATTEMPT_NUMBER NUMBER,
    P_DATASET_ID VARCHAR,
    P_CHECK_TYPE VARCHAR,
    P_CHECK_NAME VARCHAR,
    P_STATUS VARCHAR,
    P_MEASURE_NAME VARCHAR,
    P_OBSERVED_VALUE VARIANT,
    P_EXPECTED_VALUE VARIANT,
    P_DETAILS VARIANT
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
BEGIN
    INSERT INTO PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECK_RESULT (
        RUN_ID,
        ATTEMPT_NUMBER,
        PROJECT_CODE,
        ENVIRONMENT,
        DATASET_ID,
        CHECK_TYPE,
        CHECK_NAME,
        STATUS,
        MEASURE_NAME,
        OBSERVED_VALUE,
        EXPECTED_VALUE,
        DETAILS,
        CHECKED_AT,
        RECORDED_BY
    ) VALUES (
        :P_RUN_ID,
        :P_ATTEMPT_NUMBER,
        {_sql_literal(code)},
        {_sql_literal(environment)},
        LOWER(TRIM(:P_DATASET_ID)),
        LOWER(TRIM(:P_CHECK_TYPE)),
        :P_CHECK_NAME,
        UPPER(TRIM(:P_STATUS)),
        :P_MEASURE_NAME,
        :P_OBSERVED_VALUE,
        :P_EXPECTED_VALUE,
        :P_DETAILS,
        CURRENT_TIMESTAMP(),
        CURRENT_USER()
    );

    RETURN 'pipeline check result recorded';
END;
$$;
"""


def _grants(code: str) -> str:
    role = f"AR_{code}_DEPLOY"
    objects = [
        f"{code}_PIPELINE_CHECKPOINT",
        f"{code}_PIPELINE_RUN",
        f"{code}_PIPELINE_CHECK_RESULT",
    ]
    procedures = [
        (f"{code}_ADVANCE_PIPELINE_CHECKPOINT", "VARCHAR, VARCHAR, VARIANT, VARCHAR, VARCHAR"),
        (f"{code}_PIPELINE_RUN_START", "VARCHAR, NUMBER, VARCHAR, VARCHAR, VARCHAR, VARIANT, VARIANT"),
        (f"{code}_PIPELINE_RUN_FINISH", "VARCHAR, NUMBER, VARCHAR, VARIANT, NUMBER, NUMBER, NUMBER, NUMBER, NUMBER, VARCHAR, VARCHAR, VARIANT"),
        (f"{code}_RECORD_PIPELINE_CHECK_RESULT", "VARCHAR, NUMBER, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARIANT, VARIANT, VARIANT"),
    ]

    lines = [
        f"GRANT USAGE ON DATABASE PLATFORM_CONTROL TO ROLE {role};",
        f"GRANT USAGE ON SCHEMA PLATFORM_CONTROL.OPERATIONS TO ROLE {role};",
    ]
    lines.extend(
        f"GRANT SELECT ON VIEW PLATFORM_CONTROL.OPERATIONS.{name} TO ROLE {role};"
        for name in objects
    )
    lines.extend(
        f"GRANT USAGE ON PROCEDURE PLATFORM_CONTROL.OPERATIONS.{name}({signature}) TO ROLE {role};"
        for name, signature in procedures
    )
    return "\n".join(lines) + "\n"


def render(config: dict) -> str:
    environment = _identifier(config.get("environment"), "environment")
    if environment not in _ALLOWED_ENVIRONMENTS:
        raise ValueError(f"unsupported environment: {environment}")

    projects = config.get("projects")
    if not isinstance(projects, dict) or not projects:
        raise ValueError("projects must be a non-empty mapping")

    sections = [
        "-- GENERATED FILE: domain-scoped PLATFORM_CONTROL operational access.\n"
        "-- Source of truth: config/environments/<env>.yml projects metadata.\n"
        "-- Project roles receive no DML on the shared operational base tables.\n"
    ]

    for project_key in sorted(projects):
        project = projects[project_key]
        if not isinstance(project, dict):
            raise ValueError(f"projects.{project_key} must be a mapping")
        code = _identifier(project.get("code"), f"projects.{project_key}.code")
        sections.append(f"\n-- Domain: {code}; environment: {environment}\n")
        sections.append(_view_sql(code, "PIPELINE_CHECKPOINT"))
        sections.append(_view_sql(code, "PIPELINE_RUN"))
        sections.append(_view_sql(code, "PIPELINE_CHECK_RESULT"))
        sections.append(_checkpoint_procedure(code))
        sections.append(_run_start_procedure(code, environment))
        sections.append(_run_finish_procedure(code, environment))
        sections.append(_check_result_procedure(code, environment))
        sections.append(_grants(code))

    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    sql = render(config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(sql, encoding="utf-8")


if __name__ == "__main__":
    main()
