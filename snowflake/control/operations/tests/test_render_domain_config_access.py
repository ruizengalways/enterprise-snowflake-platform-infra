from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "config" / "render_domain_config_access.py"
SPEC = importlib.util.spec_from_file_location("render_domain_config_access", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RenderDomainConfigAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "environment": "dev",
            "projects": {
                "health": {"code": "HEALTH"},
                "transport": {"code": "TRANSPORT"},
            },
        }

    def test_renders_domain_and_environment_fixed_surface(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("PLATFORM_CONTROL.CONFIG.HEALTH_DATASET_CONFIG_SNAPSHOT", sql)
        self.assertIn("PROJECT_CODE = 'HEALTH'", sql)
        self.assertIn("ENVIRONMENT = 'DEV'", sql)
        self.assertIn("PLATFORM_CONTROL.CONFIG.TRANSPORT_REGISTER_DATASET_CONFIG_SNAPSHOT", sql)
        self.assertNotIn("P_PROJECT_CODE", sql)
        self.assertNotIn("P_ENVIRONMENT", sql)

    def test_registration_is_idempotent_and_conflict_safe(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("E_CONFIG_CONFLICT", sql)
        self.assertIn("dataset config snapshot already registered", sql)
        self.assertIn("REGEXP_LIKE(TRIM(P_CONFIG_HASH)", sql)
        self.assertIn("V_EXISTING_CONFIG_JSON <> TO_JSON(P_CONFIG)", sql)

    def test_project_role_has_only_view_and_procedure_access(self) -> None:
        sql = MODULE.render(self.config).upper()
        self.assertIn("GRANT SELECT ON VIEW PLATFORM_CONTROL.CONFIG.HEALTH_DATASET_CONFIG_SNAPSHOT TO ROLE AR_HEALTH_DEPLOY", sql)
        self.assertIn("GRANT USAGE ON PROCEDURE PLATFORM_CONTROL.CONFIG.HEALTH_REGISTER_DATASET_CONFIG_SNAPSHOT", sql)
        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES"):
            self.assertNotIn(
                f"GRANT {privilege} ON TABLE PLATFORM_CONTROL.CONFIG.DATASET_CONFIG_SNAPSHOT TO ROLE AR_HEALTH_DEPLOY",
                sql,
            )

    def test_invalid_project_code_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.render({"environment": "dev", "projects": {"bad": {"code": "bad-role;drop"}}})


if __name__ == "__main__":
    unittest.main()
