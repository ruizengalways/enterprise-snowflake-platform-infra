#!/usr/bin/env python3
"""Render one ordered PLATFORM_CONTROL deployment bundle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

OPERATIONS_DIR = Path(__file__).resolve().parent
CONFIG_DIR = OPERATIONS_DIR.parent / "config"
for module_dir in (OPERATIONS_DIR, CONFIG_DIR):
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))

from render_domain_access import render as render_domain_access
from render_domain_bootstrap_access import render as render_domain_bootstrap_access
from render_domain_config_access import render as render_domain_config_access


OPERATIONS_BASE_SQL_FILES = (
    "pipeline_checkpoint.sql",
    "pipeline_run.sql",
    "pipeline_check_result.sql",
    "pipeline_bootstrap.sql",
    "advance_pipeline_checkpoint.sql",
)
CONFIG_BASE_SQL_FILES = ("dataset_config_snapshot.sql",)
# Backwards-compatible alias used by existing focused tests.
BASE_SQL_FILES = OPERATIONS_BASE_SQL_FILES


def _append_base_sql(sections: list[str], directory: Path, filename: str, family: str) -> None:
    path = directory / filename
    if not path.is_file():
        raise FileNotFoundError(f"required base SQL file not found: {path}")
    sections.append(f"\n-- BEGIN BASE: {filename}\n-- Control family: {family}\n")
    sections.append(path.read_text(encoding="utf-8").rstrip() + "\n")
    sections.append(f"-- END BASE: {filename}\n")


def render_bundle(
    config: dict,
    operations_dir: Path = OPERATIONS_DIR,
    config_dir: Path = CONFIG_DIR,
) -> str:
    sections: list[str] = [
        "-- GENERATED DEPLOYMENT BUNDLE: PLATFORM_CONTROL\n"
        "-- Base objects are repository SQL; domain surfaces are rendered from environment metadata.\n"
        "-- Do not edit generated output.\n"
    ]

    for filename in OPERATIONS_BASE_SQL_FILES:
        _append_base_sql(sections, operations_dir, filename, "OPERATIONS")
    for filename in CONFIG_BASE_SQL_FILES:
        _append_base_sql(sections, config_dir, filename, "CONFIG")

    sections.append("\n-- BEGIN GENERATED: normal domain operational access\n")
    sections.append(render_domain_access(config).rstrip() + "\n")
    sections.append("-- END GENERATED: normal domain operational access\n")

    sections.append("\n-- BEGIN GENERATED: bootstrap handoff access\n")
    sections.append(render_domain_bootstrap_access(config).rstrip() + "\n")
    sections.append("-- END GENERATED: bootstrap handoff access\n")

    sections.append("\n-- BEGIN GENERATED: dataset config snapshot access\n")
    sections.append(render_domain_config_access(config).rstrip() + "\n")
    sections.append("-- END GENERATED: dataset config snapshot access\n")

    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    bundle = render_bundle(config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(bundle, encoding="utf-8")


if __name__ == "__main__":
    main()
