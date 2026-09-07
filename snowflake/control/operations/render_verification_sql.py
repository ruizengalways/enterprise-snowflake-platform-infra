#!/usr/bin/env python3
"""Render post-deployment verification SQL for PLATFORM_CONTROL."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

_IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9_]{0,62}[A-Z0-9]$|^[A-Z]$")
_ALLOWED_ENVIRONMENTS = {"DEV", "UAT", "PROD"}

_NORMAL_VIEWS = ("PIPELINE_CHECKPOINT", "PIPELINE_RUN", "PIPELINE_CHECK_RESULT")
_BOOTSTRAP_VIEWS = ("PIPELINE_BOOTSTRAP",)
_RESET_VIEWS = ("DATASET_LIFECYCLE", "DATASET_RESET")
_NORMAL_PROCEDURES = (
    "ADVANCE_PIPELINE_CHECKPOINT", "PIPELINE_RUN_START", "PIPELINE_RUN_FINISH", "RECORD_PIPELINE_CHECK_RESULT",
)
_BOOTSTRAP_PROCEDURES = (
    "PIPELINE_BOOTSTRAP_START", "PIPELINE_BOOTSTRAP_MARK_SNAPSHOT_LANDED",
    "PIPELINE_BOOTSTRAP_MARK_VALIDATED", "PIPELINE_BOOTSTRAP_COMMIT_HANDOFF",
)
_RESET_PROCEDURES = ("DATASET_RESET_START", "DATASET_RESET_COMPLETE")
_CONFIG_VIEWS = ("DATASET_CONFIG_SNAPSHOT",)
_CONFIG_PROCEDURES = ("REGISTER_DATASET_CONFIG_SNAPSHOT",)
_SHARED_BASE_TABLES = (
    "PIPELINE_CHECKPOINT", "PIPELINE_RUN", "PIPELINE_CHECK_RESULT", "PIPELINE_BOOTSTRAP",
    "DATASET_LIFECYCLE", "DATASET_RESET",
)
_CONFIG_BASE_TABLES = ("DATASET_CONFIG_SNAPSHOT",)


def _identifier(value: object, field: str) -> str:
    text = str(value or "").strip().upper()
    if not _IDENTIFIER.fullmatch(text):
        raise ValueError(f"{field} must be an unquoted Snowflake-safe identifier, got {value!r}")
    return text


def _project_codes(config: dict) -> tuple[str, list[str]]:
    environment = _identifier(config.get("environment"), "environment")
    if environment not in _ALLOWED_ENVIRONMENTS:
        raise ValueError(f"unsupported environment: {environment}")
    projects = config.get("projects")
    if not isinstance(projects, dict) or not projects:
        raise ValueError("projects must be a non-empty mapping")
    codes = []
    for key in sorted(projects):
        project = projects[key]
        if not isinstance(project, dict):
            raise ValueError(f"projects.{key} must be a mapping")
        codes.append(_identifier(project.get("code"), f"projects.{key}.code"))
    return environment, codes


def _existence_check(relation: str, name_column: str, schema_column: str, schema: str, object_name: str, label: str) -> str:
    return f"""    -- {label}
    SELECT COUNT(*) INTO :V_COUNT
    FROM PLATFORM_CONTROL.INFORMATION_SCHEMA.{relation}
    WHERE {name_column} = '{object_name}'
      AND {schema_column} = '{schema}';
    IF (V_COUNT <> 1) THEN
        RAISE E_OBJECT_MISSING;
    END IF;
"""


def _grant_check(role: str, schema: str, object_name: str, object_type: str, privilege: str) -> str:
    return f"""    -- {role}: {privilege} on {object_type} {schema}.{object_name}
    SELECT COUNT(*) INTO :V_COUNT
    FROM PLATFORM_CONTROL.INFORMATION_SCHEMA.OBJECT_PRIVILEGES
    WHERE GRANTEE = '{role}'
      AND OBJECT_CATALOG = 'PLATFORM_CONTROL'
      AND OBJECT_SCHEMA = '{schema}'
      AND OBJECT_NAME = '{object_name}'
      AND OBJECT_TYPE = '{object_type}'
      AND PRIVILEGE_TYPE = '{privilege}';
    IF (V_COUNT <> 1) THEN
        RAISE E_GRANT_MISSING;
    END IF;
"""


def _forbidden_base_grants(role: str) -> str:
    operations_names = ", ".join(f"'{name}'" for name in _SHARED_BASE_TABLES)
    config_names = ", ".join(f"'{name}'" for name in _CONFIG_BASE_TABLES)
    return f"""    -- {role} must never receive direct shared-base-table privileges.
    SELECT COUNT(*) INTO :V_COUNT
    FROM PLATFORM_CONTROL.INFORMATION_SCHEMA.OBJECT_PRIVILEGES
    WHERE GRANTEE = '{role}'
      AND OBJECT_CATALOG = 'PLATFORM_CONTROL'
      AND OBJECT_TYPE = 'TABLE'
      AND PRIVILEGE_TYPE IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES')
      AND (
          (OBJECT_SCHEMA = 'OPERATIONS' AND OBJECT_NAME IN ({operations_names}))
          OR (OBJECT_SCHEMA = 'CONFIG' AND OBJECT_NAME IN ({config_names}))
      );
    IF (V_COUNT <> 0) THEN
        RAISE E_FORBIDDEN_GRANT;
    END IF;
"""


def render(config: dict) -> str:
    environment, codes = _project_codes(config)
    lines = [
        "-- GENERATED FILE: post-deployment verification for PLATFORM_CONTROL.",
        f"-- Environment metadata: {environment}.",
        "EXECUTE IMMEDIATE $$",
        "DECLARE",
        "    E_OBJECT_MISSING EXCEPTION (-20201, 'expected PLATFORM_CONTROL domain object is missing');",
        "    E_GRANT_MISSING EXCEPTION (-20202, 'expected domain-role object grant is missing');",
        "    E_FORBIDDEN_GRANT EXCEPTION (-20203, 'domain role has direct privilege on shared PLATFORM_CONTROL base table');",
        "    V_COUNT NUMBER DEFAULT 0;",
        "BEGIN",
    ]

    for code in codes:
        deploy_role = f"AR_{code}_DEPLOY"
        recovery_role = f"AR_{code}_RECOVERY"
        lines.append(f"    -- Verify {code} deploy runtime/bootstrap surfaces.")
        for suffix in (*_NORMAL_VIEWS, *_BOOTSTRAP_VIEWS):
            name = f"{code}_{suffix}"
            lines.append(_existence_check("VIEWS", "TABLE_NAME", "TABLE_SCHEMA", "OPERATIONS", name, f"domain view {name}"))
            lines.append(_grant_check(deploy_role, "OPERATIONS", name, "VIEW", "SELECT"))
        for suffix in (*_NORMAL_PROCEDURES, *_BOOTSTRAP_PROCEDURES):
            name = f"{code}_{suffix}"
            lines.append(_existence_check("PROCEDURES", "PROCEDURE_NAME", "PROCEDURE_SCHEMA", "OPERATIONS", name, f"owner-rights procedure {name}"))
            lines.append(_grant_check(deploy_role, "OPERATIONS", name, "PROCEDURE", "USAGE"))

        lines.append(f"    -- Verify {code} Senior Data Engineer+ recovery surface.")
        for suffix in _RESET_VIEWS:
            name = f"{code}_{suffix}"
            lines.append(_existence_check("VIEWS", "TABLE_NAME", "TABLE_SCHEMA", "OPERATIONS", name, f"recovery view {name}"))
            lines.append(_grant_check(recovery_role, "OPERATIONS", name, "VIEW", "SELECT"))
        for suffix in _RESET_PROCEDURES:
            name = f"{code}_{suffix}"
            lines.append(_existence_check("PROCEDURES", "PROCEDURE_NAME", "PROCEDURE_SCHEMA", "OPERATIONS", name, f"recovery procedure {name}"))
            lines.append(_grant_check(recovery_role, "OPERATIONS", name, "PROCEDURE", "USAGE"))

        lines.append(f"    -- Verify {code} dataset configuration audit surface.")
        for suffix in _CONFIG_VIEWS:
            name = f"{code}_{suffix}"
            lines.append(_existence_check("VIEWS", "TABLE_NAME", "TABLE_SCHEMA", "CONFIG", name, f"config view {name}"))
            lines.append(_grant_check(deploy_role, "CONFIG", name, "VIEW", "SELECT"))
        for suffix in _CONFIG_PROCEDURES:
            name = f"{code}_{suffix}"
            lines.append(_existence_check("PROCEDURES", "PROCEDURE_NAME", "PROCEDURE_SCHEMA", "CONFIG", name, f"config procedure {name}"))
            lines.append(_grant_check(deploy_role, "CONFIG", name, "PROCEDURE", "USAGE"))

        lines.append(_forbidden_base_grants(deploy_role))
        lines.append(_forbidden_base_grants(recovery_role))

    lines.extend(["    RETURN 'platform-control deployment verification passed';", "END;", "$$;", ""])
    return "\n".join(lines)


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
