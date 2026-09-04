#!/usr/bin/env python3
"""Render domain-scoped access to Git-owned dataset configuration snapshots."""

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
    name = f"{code}_DATASET_CONFIG_SNAPSHOT"
    return f"""CREATE OR REPLACE SECURE VIEW PLATFORM_CONTROL.CONFIG.{name} AS
SELECT
    DATASET_ID,
    CONFIG_SCHEMA_VERSION,
    GIT_SHA,
    CONFIG_HASH,
    CONFIG,
    DEPLOYED_AT,
    DEPLOYED_BY
FROM PLATFORM_CONTROL.CONFIG.DATASET_CONFIG_SNAPSHOT
WHERE PROJECT_CODE = {_sql_literal(code)}
  AND ENVIRONMENT = {_sql_literal(environment)};
"""


def _register_procedure_sql(code: str, environment: str) -> str:
    name = f"{code}_REGISTER_DATASET_CONFIG_SNAPSHOT"
    return f"""CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.CONFIG.{name}(
    P_DATASET_ID VARCHAR,
    P_CONFIG_SCHEMA_VERSION NUMBER,
    P_GIT_SHA VARCHAR,
    P_CONFIG_HASH VARCHAR,
    P_CONFIG VARIANT
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
    E_INVALID_CONFIG EXCEPTION (-20301, 'dataset config snapshot arguments are invalid');
    E_CONFIG_CONFLICT EXCEPTION (-20302, 'dataset config snapshot conflicts with an existing Git revision');
    V_COUNT NUMBER DEFAULT 0;
    V_EXISTING_HASH VARCHAR;
    V_EXISTING_CONFIG_JSON VARCHAR;
BEGIN
    IF (P_DATASET_ID IS NULL OR TRIM(P_DATASET_ID) = ''
        OR P_CONFIG_SCHEMA_VERSION IS NULL OR P_CONFIG_SCHEMA_VERSION < 1
        OR P_GIT_SHA IS NULL OR TRIM(P_GIT_SHA) = ''
        OR P_CONFIG_HASH IS NULL OR NOT REGEXP_LIKE(TRIM(P_CONFIG_HASH), '^[0-9A-Fa-f]{{64}}$')
        OR P_CONFIG IS NULL) THEN
        RAISE E_INVALID_CONFIG;
    END IF;

    SELECT COUNT(*) INTO :V_COUNT
    FROM PLATFORM_CONTROL.CONFIG.DATASET_CONFIG_SNAPSHOT
    WHERE PROJECT_CODE = {_sql_literal(code)}
      AND ENVIRONMENT = {_sql_literal(environment)}
      AND DATASET_ID = LOWER(TRIM(:P_DATASET_ID))
      AND GIT_SHA = TRIM(:P_GIT_SHA);

    IF (V_COUNT > 0) THEN
        SELECT CONFIG_HASH, TO_JSON(CONFIG)
          INTO :V_EXISTING_HASH, :V_EXISTING_CONFIG_JSON
        FROM PLATFORM_CONTROL.CONFIG.DATASET_CONFIG_SNAPSHOT
        WHERE PROJECT_CODE = {_sql_literal(code)}
          AND ENVIRONMENT = {_sql_literal(environment)}
          AND DATASET_ID = LOWER(TRIM(:P_DATASET_ID))
          AND GIT_SHA = TRIM(:P_GIT_SHA)
        LIMIT 1;

        IF (LOWER(V_EXISTING_HASH) <> LOWER(TRIM(P_CONFIG_HASH))
            OR V_EXISTING_CONFIG_JSON <> TO_JSON(P_CONFIG)) THEN
            RAISE E_CONFIG_CONFLICT;
        END IF;

        RETURN 'dataset config snapshot already registered';
    END IF;

    INSERT INTO PLATFORM_CONTROL.CONFIG.DATASET_CONFIG_SNAPSHOT (
        PROJECT_CODE,
        ENVIRONMENT,
        DATASET_ID,
        CONFIG_SCHEMA_VERSION,
        GIT_SHA,
        CONFIG_HASH,
        CONFIG,
        DEPLOYED_AT,
        DEPLOYED_BY
    ) VALUES (
        {_sql_literal(code)},
        {_sql_literal(environment)},
        LOWER(TRIM(:P_DATASET_ID)),
        :P_CONFIG_SCHEMA_VERSION,
        TRIM(:P_GIT_SHA),
        LOWER(TRIM(:P_CONFIG_HASH)),
        :P_CONFIG,
        CURRENT_TIMESTAMP(),
        CURRENT_USER()
    );

    RETURN 'dataset config snapshot registered';
END;
$$;
"""


def _grants(code: str) -> str:
    role = f"AR_{code}_DEPLOY"
    view = f"{code}_DATASET_CONFIG_SNAPSHOT"
    procedure = f"{code}_REGISTER_DATASET_CONFIG_SNAPSHOT"
    return "\n".join(
        [
            f"GRANT USAGE ON DATABASE PLATFORM_CONTROL TO ROLE {role};",
            f"GRANT USAGE ON SCHEMA PLATFORM_CONTROL.CONFIG TO ROLE {role};",
            f"GRANT SELECT ON VIEW PLATFORM_CONTROL.CONFIG.{view} TO ROLE {role};",
            f"GRANT USAGE ON PROCEDURE PLATFORM_CONTROL.CONFIG.{procedure}(VARCHAR, NUMBER, VARCHAR, VARCHAR, VARIANT) TO ROLE {role};",
            "",
        ]
    )


def render(config: dict) -> str:
    environment = _identifier(config.get("environment"), "environment")
    if environment not in _ALLOWED_ENVIRONMENTS:
        raise ValueError(f"unsupported environment: {environment}")

    projects = config.get("projects")
    if not isinstance(projects, dict) or not projects:
        raise ValueError("projects must be a non-empty mapping")

    sections = [
        "-- GENERATED FILE: domain-scoped PLATFORM_CONTROL dataset-config access.\n"
        "-- Git is the configuration source of truth; this surface records immutable deployment snapshots.\n"
        "-- Project roles receive no DML on the shared DATASET_CONFIG_SNAPSHOT base table.\n"
    ]

    for project_key in sorted(projects):
        project = projects[project_key]
        if not isinstance(project, dict):
            raise ValueError(f"projects.{project_key} must be a mapping")
        code = _identifier(project.get("code"), f"projects.{project_key}.code")
        sections.append(f"\n-- Domain: {code}; environment: {environment}\n")
        sections.append(_view_sql(code, environment))
        sections.append(_register_procedure_sql(code, environment))
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
