#!/usr/bin/env python3
"""Render domain-scoped full-reset lifecycle APIs."""

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
        raise ValueError(f"{field} must be a Snowflake-safe identifier, got {value!r}")
    return text


def _lit(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _views(code: str, environment: str) -> str:
    return f"""CREATE OR REPLACE SECURE VIEW PLATFORM_CONTROL.OPERATIONS.{code}_DATASET_LIFECYCLE AS
SELECT *
FROM PLATFORM_CONTROL.OPERATIONS.DATASET_LIFECYCLE
WHERE PROJECT_CODE = {_lit(code)}
  AND ENVIRONMENT = {_lit(environment)};

CREATE OR REPLACE SECURE VIEW PLATFORM_CONTROL.OPERATIONS.{code}_DATASET_RESET AS
SELECT *
FROM PLATFORM_CONTROL.OPERATIONS.DATASET_RESET
WHERE PROJECT_CODE = {_lit(code)}
  AND ENVIRONMENT = {_lit(environment)};
"""


def _start_proc(code: str, environment: str) -> str:
    name = f"{code}_DATASET_RESET_START"
    return f"""CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.OPERATIONS.{name}(
    P_RESET_ID VARCHAR,
    P_DATASET_ID VARCHAR,
    P_REASON VARCHAR,
    P_GIT_SHA VARCHAR,
    P_DETAILS VARIANT
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
    V_DATASET_ID VARCHAR;
    V_GENERATION NUMBER;
    V_STATE VARCHAR;
    V_EXISTING_COUNT NUMBER;
    V_RUNNING_COUNT NUMBER;
BEGIN
    V_DATASET_ID := LOWER(TRIM(:P_DATASET_ID));
    IF COALESCE(TRIM(:P_RESET_ID), '') = '' THEN
        RAISE STATEMENT_ERROR WITH MESSAGE = 'reset_id is required';
    END IF;
    IF COALESCE(V_DATASET_ID, '') = '' THEN
        RAISE STATEMENT_ERROR WITH MESSAGE = 'dataset_id is required';
    END IF;
    IF COALESCE(TRIM(:P_REASON), '') = '' THEN
        RAISE STATEMENT_ERROR WITH MESSAGE = 'reset reason is required';
    END IF;

    SELECT COUNT(*) INTO :V_EXISTING_COUNT
    FROM PLATFORM_CONTROL.OPERATIONS.DATASET_RESET
    WHERE RESET_ID = :P_RESET_ID;

    IF V_EXISTING_COUNT > 0 THEN
        SELECT COUNT(*) INTO :V_EXISTING_COUNT
        FROM PLATFORM_CONTROL.OPERATIONS.DATASET_RESET
        WHERE RESET_ID = :P_RESET_ID
          AND PROJECT_CODE = {_lit(code)}
          AND ENVIRONMENT = {_lit(environment)}
          AND DATASET_ID = :V_DATASET_ID;
        IF V_EXISTING_COUNT = 0 THEN
            RAISE STATEMENT_ERROR WITH MESSAGE = 'reset_id already belongs to a different dataset';
        END IF;
        RETURN 'reset already started';
    END IF;

    MERGE INTO PLATFORM_CONTROL.OPERATIONS.DATASET_LIFECYCLE AS target
    USING (
        SELECT {_lit(code)} PROJECT_CODE,
               {_lit(environment)} ENVIRONMENT,
               :V_DATASET_ID DATASET_ID
    ) source
      ON target.PROJECT_CODE = source.PROJECT_CODE
     AND target.ENVIRONMENT = source.ENVIRONMENT
     AND target.DATASET_ID = source.DATASET_ID
    WHEN NOT MATCHED THEN INSERT (
        PROJECT_CODE, ENVIRONMENT, DATASET_ID, CURRENT_GENERATION, STATE
    ) VALUES (
        source.PROJECT_CODE, source.ENVIRONMENT, source.DATASET_ID, 1, 'ACTIVE'
    );

    SELECT CURRENT_GENERATION, STATE
      INTO :V_GENERATION, :V_STATE
    FROM PLATFORM_CONTROL.OPERATIONS.DATASET_LIFECYCLE
    WHERE PROJECT_CODE = {_lit(code)}
      AND ENVIRONMENT = {_lit(environment)}
      AND DATASET_ID = :V_DATASET_ID;

    IF V_STATE = 'RESETTING' THEN
        RAISE STATEMENT_ERROR WITH MESSAGE = 'dataset already has a reset in progress';
    END IF;

    SELECT COUNT(*) INTO :V_RUNNING_COUNT
    FROM PLATFORM_CONTROL.OPERATIONS.PIPELINE_RUN
    WHERE PROJECT_CODE = {_lit(code)}
      AND ENVIRONMENT = {_lit(environment)}
      AND DATASET_ID = :V_DATASET_ID
      AND GENERATION = :V_GENERATION
      AND STATUS = 'RUNNING';

    IF V_RUNNING_COUNT > 0 THEN
        RAISE STATEMENT_ERROR WITH MESSAGE = 'cannot reset while a current-generation pipeline run is RUNNING';
    END IF;

    INSERT INTO PLATFORM_CONTROL.OPERATIONS.DATASET_RESET (
        RESET_ID, PROJECT_CODE, ENVIRONMENT, DATASET_ID,
        FROM_GENERATION, TO_GENERATION, STATUS, REASON, GIT_SHA, DETAILS,
        RESET_STARTED_AT
    ) VALUES (
        :P_RESET_ID, {_lit(code)}, {_lit(environment)}, :V_DATASET_ID,
        :V_GENERATION, :V_GENERATION + 1, 'RESETTING', TRIM(:P_REASON),
        :P_GIT_SHA, :P_DETAILS, CURRENT_TIMESTAMP()
    );

    UPDATE PLATFORM_CONTROL.OPERATIONS.DATASET_LIFECYCLE
    SET STATE = 'RESETTING',
        LAST_RESET_ID = :P_RESET_ID,
        ROW_VERSION = ROW_VERSION + 1,
        UPDATED_AT = CURRENT_TIMESTAMP(),
        UPDATED_BY = CURRENT_USER()
    WHERE PROJECT_CODE = {_lit(code)}
      AND ENVIRONMENT = {_lit(environment)}
      AND DATASET_ID = :V_DATASET_ID;

    RETURN 'reset started';
END;
$$;
"""


def _complete_proc(code: str, environment: str) -> str:
    name = f"{code}_DATASET_RESET_COMPLETE"
    return f"""CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.OPERATIONS.{name}(
    P_RESET_ID VARCHAR,
    P_DATASET_ID VARCHAR,
    P_DETAILS VARIANT
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
    V_DATASET_ID VARCHAR;
    V_STATUS VARCHAR;
    V_TO_GENERATION NUMBER;
BEGIN
    V_DATASET_ID := LOWER(TRIM(:P_DATASET_ID));

    SELECT STATUS, TO_GENERATION
      INTO :V_STATUS, :V_TO_GENERATION
    FROM PLATFORM_CONTROL.OPERATIONS.DATASET_RESET
    WHERE RESET_ID = :P_RESET_ID
      AND PROJECT_CODE = {_lit(code)}
      AND ENVIRONMENT = {_lit(environment)}
      AND DATASET_ID = :V_DATASET_ID;

    IF V_STATUS IN ('READY_FOR_RELOAD', 'COMPLETED') THEN
        RETURN 'reset already completed';
    END IF;
    IF V_STATUS <> 'RESETTING' THEN
        RAISE STATEMENT_ERROR WITH MESSAGE = 'reset must be RESETTING before completion';
    END IF;

    BEGIN TRANSACTION;

    UPDATE PLATFORM_CONTROL.OPERATIONS.DATASET_LIFECYCLE
    SET CURRENT_GENERATION = :V_TO_GENERATION,
        STATE = 'READY_FOR_INITIAL_LOAD',
        LAST_RESET_ID = :P_RESET_ID,
        ROW_VERSION = ROW_VERSION + 1,
        UPDATED_AT = CURRENT_TIMESTAMP(),
        UPDATED_BY = CURRENT_USER()
    WHERE PROJECT_CODE = {_lit(code)}
      AND ENVIRONMENT = {_lit(environment)}
      AND DATASET_ID = :V_DATASET_ID
      AND STATE = 'RESETTING';

    UPDATE PLATFORM_CONTROL.OPERATIONS.DATASET_RESET
    SET STATUS = 'READY_FOR_RELOAD',
        DETAILS = COALESCE(:P_DETAILS, DETAILS),
        READY_FOR_RELOAD_AT = CURRENT_TIMESTAMP(),
        UPDATED_AT = CURRENT_TIMESTAMP(),
        UPDATED_BY = CURRENT_USER()
    WHERE RESET_ID = :P_RESET_ID;

    COMMIT;
    RETURN 'reset ready for initial load';
END;
$$;
"""


def _grants(code: str) -> str:
    role = f"AR_{code}_RECOVERY"
    return f"""GRANT USAGE ON DATABASE PLATFORM_CONTROL TO ROLE {role};
GRANT USAGE ON SCHEMA PLATFORM_CONTROL.OPERATIONS TO ROLE {role};
GRANT SELECT ON VIEW PLATFORM_CONTROL.OPERATIONS.{code}_DATASET_LIFECYCLE TO ROLE {role};
GRANT SELECT ON VIEW PLATFORM_CONTROL.OPERATIONS.{code}_DATASET_RESET TO ROLE {role};
GRANT USAGE ON PROCEDURE PLATFORM_CONTROL.OPERATIONS.{code}_DATASET_RESET_START(VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARIANT) TO ROLE {role};
GRANT USAGE ON PROCEDURE PLATFORM_CONTROL.OPERATIONS.{code}_DATASET_RESET_COMPLETE(VARCHAR, VARCHAR, VARIANT) TO ROLE {role};
"""


def render(config: dict) -> str:
    environment = _identifier(config.get("environment"), "environment")
    if environment not in _ALLOWED_ENVIRONMENTS:
        raise ValueError(f"unsupported environment: {environment}")
    projects = config.get("projects")
    if not isinstance(projects, dict) or not projects:
        raise ValueError("projects must be a non-empty mapping")

    sections = [
        "-- GENERATED FILE: domain-scoped full dataset reset access.\n"
        "-- Reset is distinct from repair/replay. Recovery roles do not receive direct DML on control tables.\n"
    ]
    for key in sorted(projects):
        project = projects[key]
        code = _identifier(project.get("code"), f"projects.{key}.code")
        sections.append(f"\n-- Domain: {code}; environment: {environment}\n")
        sections.append(_views(code, environment))
        sections.append(_start_proc(code, environment))
        sections.append(_complete_proc(code, environment))
        sections.append(_grants(code))
    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(config), encoding="utf-8")


if __name__ == "__main__":
    main()
