#!/usr/bin/env python3
"""Render domain-scoped bootstrap handoff views, procedures, and grants."""

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


def _view_sql(code: str, environment: str) -> str:
    return f"""CREATE OR REPLACE SECURE VIEW PLATFORM_CONTROL.OPERATIONS.{code}_PIPELINE_BOOTSTRAP AS
SELECT *
FROM PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP
WHERE PROJECT_CODE = {_sql_literal(code)}
  AND ENVIRONMENT = {_sql_literal(environment)};
"""


def _start_procedure(code: str, environment: str) -> str:
    return f"""CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.OPERATIONS.{code}_PIPELINE_BOOTSTRAP_START(
    P_DATASET_ID VARCHAR,
    P_BOOTSTRAP_ID VARCHAR,
    P_CHECKPOINT_KIND VARCHAR,
    P_HANDOFF_POSITION VARIANT,
    P_INCREMENTAL_START VARCHAR,
    P_GIT_SHA VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
    E_CONFLICT EXCEPTION (-20101, 'bootstrap_id already exists with different boundary metadata');
    E_CHECKPOINT_EXISTS EXCEPTION (-20107, 'initial bootstrap cannot start after steady-state checkpoint exists');
    V_EXISTING NUMBER DEFAULT 0;
    V_CONFLICT NUMBER DEFAULT 0;
    V_CHECKPOINT_EXISTS NUMBER DEFAULT 0;
BEGIN
    SELECT COUNT(*) INTO :V_EXISTING
    FROM PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP
    WHERE PROJECT_CODE = {_sql_literal(code)}
      AND ENVIRONMENT = {_sql_literal(environment)}
      AND DATASET_ID = LOWER(TRIM(:P_DATASET_ID))
      AND BOOTSTRAP_ID = :P_BOOTSTRAP_ID;

    IF (V_EXISTING > 0) THEN
        SELECT COUNT(*) INTO :V_CONFLICT
        FROM PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP
        WHERE PROJECT_CODE = {_sql_literal(code)}
          AND ENVIRONMENT = {_sql_literal(environment)}
          AND DATASET_ID = LOWER(TRIM(:P_DATASET_ID))
          AND BOOTSTRAP_ID = :P_BOOTSTRAP_ID
          AND (
              HANDOFF_CHECKPOINT_KIND <> LOWER(TRIM(:P_CHECKPOINT_KIND))
              OR INCREMENTAL_START <> LOWER(TRIM(:P_INCREMENTAL_START))
              OR NOT EQUAL_NULL(HANDOFF_POSITION, :P_HANDOFF_POSITION)
          );
        IF (V_CONFLICT > 0) THEN
            RAISE E_CONFLICT;
        END IF;
        RETURN 'bootstrap already started';
    END IF;

    SELECT COUNT(*) INTO :V_CHECKPOINT_EXISTS
    FROM PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT
    WHERE PROJECT_CODE = {_sql_literal(code)}
      AND DATASET_ID = LOWER(TRIM(:P_DATASET_ID))
      AND CHECKPOINT_KIND = LOWER(TRIM(:P_CHECKPOINT_KIND));

    IF (V_CHECKPOINT_EXISTS > 0) THEN
        RAISE E_CHECKPOINT_EXISTS;
    END IF;

    INSERT INTO PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP (
        PROJECT_CODE,
        ENVIRONMENT,
        DATASET_ID,
        BOOTSTRAP_ID,
        STATUS,
        HANDOFF_CHECKPOINT_KIND,
        HANDOFF_POSITION,
        INCREMENTAL_START,
        GIT_SHA,
        BOUNDARY_CAPTURED_AT,
        ROW_VERSION,
        UPDATED_AT,
        UPDATED_BY
    ) VALUES (
        {_sql_literal(code)},
        {_sql_literal(environment)},
        LOWER(TRIM(:P_DATASET_ID)),
        :P_BOOTSTRAP_ID,
        'BOUNDARY_CAPTURED',
        LOWER(TRIM(:P_CHECKPOINT_KIND)),
        :P_HANDOFF_POSITION,
        LOWER(TRIM(:P_INCREMENTAL_START)),
        :P_GIT_SHA,
        CURRENT_TIMESTAMP(),
        1,
        CURRENT_TIMESTAMP(),
        CURRENT_USER()
    );

    RETURN 'bootstrap boundary captured';
END;
$$;
"""


def _snapshot_landed_procedure(code: str, environment: str) -> str:
    return f"""CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.OPERATIONS.{code}_PIPELINE_BOOTSTRAP_MARK_SNAPSHOT_LANDED(
    P_DATASET_ID VARCHAR,
    P_BOOTSTRAP_ID VARCHAR,
    P_SNAPSHOT_ID VARCHAR,
    P_SNAPSHOT_BATCH_ID VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
    E_INVALID_STATE EXCEPTION (-20102, 'snapshot landed requires BOUNDARY_CAPTURED state');
    E_CONFLICT EXCEPTION (-20103, 'snapshot identity conflicts with existing bootstrap state');
    V_STATUS VARCHAR;
    V_SNAPSHOT_ID VARCHAR;
    V_SNAPSHOT_BATCH_ID VARCHAR;
BEGIN
    SELECT STATUS, SNAPSHOT_ID, SNAPSHOT_BATCH_ID
      INTO :V_STATUS, :V_SNAPSHOT_ID, :V_SNAPSHOT_BATCH_ID
    FROM PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP
    WHERE PROJECT_CODE = {_sql_literal(code)}
      AND ENVIRONMENT = {_sql_literal(environment)}
      AND DATASET_ID = LOWER(TRIM(:P_DATASET_ID))
      AND BOOTSTRAP_ID = :P_BOOTSTRAP_ID;

    IF (V_STATUS IN ('SNAPSHOT_LANDED', 'SNAPSHOT_VALIDATED', 'HANDOFF_COMMITTED')) THEN
        IF (NOT EQUAL_NULL(V_SNAPSHOT_ID, P_SNAPSHOT_ID)
            OR NOT EQUAL_NULL(V_SNAPSHOT_BATCH_ID, P_SNAPSHOT_BATCH_ID)) THEN
            RAISE E_CONFLICT;
        END IF;
        RETURN 'snapshot already recorded';
    END IF;

    IF (V_STATUS <> 'BOUNDARY_CAPTURED') THEN
        RAISE E_INVALID_STATE;
    END IF;

    UPDATE PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP
    SET STATUS = 'SNAPSHOT_LANDED',
        SNAPSHOT_ID = :P_SNAPSHOT_ID,
        SNAPSHOT_BATCH_ID = :P_SNAPSHOT_BATCH_ID,
        SNAPSHOT_LANDED_AT = CURRENT_TIMESTAMP(),
        ROW_VERSION = ROW_VERSION + 1,
        UPDATED_AT = CURRENT_TIMESTAMP(),
        UPDATED_BY = CURRENT_USER()
    WHERE PROJECT_CODE = {_sql_literal(code)}
      AND ENVIRONMENT = {_sql_literal(environment)}
      AND DATASET_ID = LOWER(TRIM(:P_DATASET_ID))
      AND BOOTSTRAP_ID = :P_BOOTSTRAP_ID
      AND STATUS = 'BOUNDARY_CAPTURED';

    RETURN 'bootstrap snapshot landed';
END;
$$;
"""


def _validated_procedure(code: str, environment: str) -> str:
    return f"""CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.OPERATIONS.{code}_PIPELINE_BOOTSTRAP_MARK_VALIDATED(
    P_DATASET_ID VARCHAR,
    P_BOOTSTRAP_ID VARCHAR,
    P_RECONCILIATION_DETAILS VARIANT
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
    E_INVALID_STATE EXCEPTION (-20104, 'bootstrap validation requires SNAPSHOT_LANDED state');
    E_DETAILS_REQUIRED EXCEPTION (-20105, 'reconciliation details are required before handoff validation');
    E_DETAILS_CONFLICT EXCEPTION (-20109, 'reconciliation details conflict with already validated bootstrap state');
    V_STATUS VARCHAR;
    V_RECONCILIATION_DETAILS VARIANT;
BEGIN
    IF (P_RECONCILIATION_DETAILS IS NULL) THEN
        RAISE E_DETAILS_REQUIRED;
    END IF;

    SELECT STATUS, RECONCILIATION_DETAILS
      INTO :V_STATUS, :V_RECONCILIATION_DETAILS
    FROM PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP
    WHERE PROJECT_CODE = {_sql_literal(code)}
      AND ENVIRONMENT = {_sql_literal(environment)}
      AND DATASET_ID = LOWER(TRIM(:P_DATASET_ID))
      AND BOOTSTRAP_ID = :P_BOOTSTRAP_ID;

    IF (V_STATUS IN ('SNAPSHOT_VALIDATED', 'HANDOFF_COMMITTED')) THEN
        IF (NOT EQUAL_NULL(V_RECONCILIATION_DETAILS, P_RECONCILIATION_DETAILS)) THEN
            RAISE E_DETAILS_CONFLICT;
        END IF;
        RETURN 'bootstrap already validated';
    END IF;

    IF (V_STATUS <> 'SNAPSHOT_LANDED') THEN
        RAISE E_INVALID_STATE;
    END IF;

    UPDATE PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP
    SET STATUS = 'SNAPSHOT_VALIDATED',
        RECONCILIATION_DETAILS = :P_RECONCILIATION_DETAILS,
        SNAPSHOT_VALIDATED_AT = CURRENT_TIMESTAMP(),
        ROW_VERSION = ROW_VERSION + 1,
        UPDATED_AT = CURRENT_TIMESTAMP(),
        UPDATED_BY = CURRENT_USER()
    WHERE PROJECT_CODE = {_sql_literal(code)}
      AND ENVIRONMENT = {_sql_literal(environment)}
      AND DATASET_ID = LOWER(TRIM(:P_DATASET_ID))
      AND BOOTSTRAP_ID = :P_BOOTSTRAP_ID
      AND STATUS = 'SNAPSHOT_LANDED';

    RETURN 'bootstrap snapshot validated';
END;
$$;
"""


def _commit_procedure(code: str, environment: str) -> str:
    return f"""CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.OPERATIONS.{code}_PIPELINE_BOOTSTRAP_COMMIT_HANDOFF(
    P_DATASET_ID VARCHAR,
    P_BOOTSTRAP_ID VARCHAR,
    P_BATCH_ID VARCHAR,
    P_GIT_SHA VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
    E_INVALID_STATE EXCEPTION (-20106, 'handoff commit requires SNAPSHOT_VALIDATED state');
    E_CHECKPOINT_CONFLICT EXCEPTION (-20108, 'existing steady-state checkpoint differs from bootstrap handoff position');
    V_STATUS VARCHAR;
    V_CHECKPOINT_KIND VARCHAR;
    V_HANDOFF_POSITION VARIANT;
    V_CHECKPOINT_CONFLICT NUMBER DEFAULT 0;
BEGIN
    SELECT STATUS, HANDOFF_CHECKPOINT_KIND, HANDOFF_POSITION
      INTO :V_STATUS, :V_CHECKPOINT_KIND, :V_HANDOFF_POSITION
    FROM PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP
    WHERE PROJECT_CODE = {_sql_literal(code)}
      AND ENVIRONMENT = {_sql_literal(environment)}
      AND DATASET_ID = LOWER(TRIM(:P_DATASET_ID))
      AND BOOTSTRAP_ID = :P_BOOTSTRAP_ID;

    IF (V_STATUS = 'HANDOFF_COMMITTED') THEN
        RETURN 'bootstrap handoff already committed';
    END IF;

    IF (V_STATUS <> 'SNAPSHOT_VALIDATED') THEN
        RAISE E_INVALID_STATE;
    END IF;

    BEGIN
        BEGIN TRANSACTION;

        SELECT COUNT(*) INTO :V_CHECKPOINT_CONFLICT
        FROM PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT
        WHERE PROJECT_CODE = {_sql_literal(code)}
          AND DATASET_ID = LOWER(TRIM(:P_DATASET_ID))
          AND CHECKPOINT_KIND = :V_CHECKPOINT_KIND
          AND NOT EQUAL_NULL(CHECKPOINT_VALUE, :V_HANDOFF_POSITION);

        IF (V_CHECKPOINT_CONFLICT > 0) THEN
            RAISE E_CHECKPOINT_CONFLICT;
        END IF;

        MERGE INTO PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT AS target
        USING (
            SELECT
                {_sql_literal(code)} AS PROJECT_CODE,
                LOWER(TRIM(:P_DATASET_ID)) AS DATASET_ID,
                :V_CHECKPOINT_KIND AS CHECKPOINT_KIND,
                :V_HANDOFF_POSITION AS CHECKPOINT_VALUE,
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

        UPDATE PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP
        SET STATUS = 'HANDOFF_COMMITTED',
            HANDOFF_COMMITTED_AT = CURRENT_TIMESTAMP(),
            GIT_SHA = :P_GIT_SHA,
            ROW_VERSION = ROW_VERSION + 1,
            UPDATED_AT = CURRENT_TIMESTAMP(),
            UPDATED_BY = CURRENT_USER()
        WHERE PROJECT_CODE = {_sql_literal(code)}
          AND ENVIRONMENT = {_sql_literal(environment)}
          AND DATASET_ID = LOWER(TRIM(:P_DATASET_ID))
          AND BOOTSTRAP_ID = :P_BOOTSTRAP_ID
          AND STATUS = 'SNAPSHOT_VALIDATED';

        COMMIT;
    EXCEPTION
        WHEN OTHER THEN
            ROLLBACK;
            RAISE;
    END;

    RETURN 'bootstrap handoff committed';
END;
$$;
"""


def _grants(code: str) -> str:
    role = f"AR_{code}_DEPLOY"
    procedures = [
        (f"{code}_PIPELINE_BOOTSTRAP_START", "VARCHAR, VARCHAR, VARCHAR, VARIANT, VARCHAR, VARCHAR"),
        (f"{code}_PIPELINE_BOOTSTRAP_MARK_SNAPSHOT_LANDED", "VARCHAR, VARCHAR, VARCHAR, VARCHAR"),
        (f"{code}_PIPELINE_BOOTSTRAP_MARK_VALIDATED", "VARCHAR, VARCHAR, VARIANT"),
        (f"{code}_PIPELINE_BOOTSTRAP_COMMIT_HANDOFF", "VARCHAR, VARCHAR, VARCHAR, VARCHAR"),
    ]
    lines = [
        f"GRANT USAGE ON DATABASE PLATFORM_CONTROL TO ROLE {role};",
        f"GRANT USAGE ON SCHEMA PLATFORM_CONTROL.OPERATIONS TO ROLE {role};",
        f"GRANT SELECT ON VIEW PLATFORM_CONTROL.OPERATIONS.{code}_PIPELINE_BOOTSTRAP TO ROLE {role};",
    ]
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
        "-- GENERATED FILE: domain-scoped bootstrap handoff access.\n"
        "-- Source of truth: config/environments/<env>.yml projects metadata.\n"
        "-- Project roles receive no direct DML on bootstrap/checkpoint base tables.\n"
    ]

    for project_key in sorted(projects):
        project = projects[project_key]
        if not isinstance(project, dict):
            raise ValueError(f"projects.{project_key} must be a mapping")
        code = _identifier(project.get("code"), f"projects.{project_key}.code")
        sections.append(f"\n-- Domain: {code}; environment: {environment}\n")
        sections.append(_view_sql(code, environment))
        sections.append(_start_procedure(code, environment))
        sections.append(_snapshot_landed_procedure(code, environment))
        sections.append(_validated_procedure(code, environment))
        sections.append(_commit_procedure(code, environment))
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
