#!/usr/bin/env python3
"""Render one ordered PLATFORM_CONTROL operations deployment bundle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

OPERATIONS_DIR = Path(__file__).resolve().parent
if str(OPERATIONS_DIR) not in sys.path:
    sys.path.insert(0, str(OPERATIONS_DIR))

from render_domain_access import render as render_domain_access
from render_domain_bootstrap_access import render as render_domain_bootstrap_access


BASE_SQL_FILES = (
    "pipeline_checkpoint.sql",
    "pipeline_run.sql",
    "pipeline_check_result.sql",
    "pipeline_bootstrap.sql",
    "advance_pipeline_checkpoint.sql",
)


def render_bundle(config: dict, operations_dir: Path = OPERATIONS_DIR) -> str:
    sections: list[str] = [
        "-- GENERATED DEPLOYMENT BUNDLE: PLATFORM_CONTROL.OPERATIONS\n"
        "-- Base objects are repository SQL; domain surfaces are rendered from environment metadata.\n"
        "-- Do not edit generated output.\n"
    ]

    for filename in BASE_SQL_FILES:
        path = operations_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"required base SQL file not found: {path}")
        sections.append(f"\n-- BEGIN BASE: {filename}\n")
        sections.append(path.read_text(encoding="utf-8").rstrip() + "\n")
        sections.append(f"-- END BASE: {filename}\n")

    sections.append("\n-- BEGIN GENERATED: normal domain operational access\n")
    sections.append(render_domain_access(config).rstrip() + "\n")
    sections.append("-- END GENERATED: normal domain operational access\n")

    sections.append("\n-- BEGIN GENERATED: bootstrap handoff access\n")
    sections.append(render_domain_bootstrap_access(config).rstrip() + "\n")
    sections.append("-- END GENERATED: bootstrap handoff access\n")

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
