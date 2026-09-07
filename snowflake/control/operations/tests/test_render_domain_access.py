from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "render_domain_access.py"
SPEC = importlib.util.spec_from_file_location("render_domain_access", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RenderDomainAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "environment": "dev",
            "projects": {
                "health": {"code": "HEALTH"},
                "transport": {"code": "TRANSPORT"},
            },
        }

    def test_renders_domain_filtered_views_and_fixed_write_apis(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("CREATE OR REPLACE SECURE VIEW PLATFORM_CONTROL.OPERATIONS.HEALTH_PIPELINE_CHECKPOINT", sql)
        self.assertIn("checkpoint.PROJECT_CODE = 'HEALTH'", sql)
        self.assertIn("checkpoint.PROJECT_CODE = 'TRANSPORT'", sql)
        self.assertIn("lifecycle.CURRENT_GENERATION", sql)
        self.assertIn("CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.OPERATIONS.HEALTH_ADVANCE_PIPELINE_CHECKPOINT(", sql)
        self.assertIn("'HEALTH' AS PROJECT_CODE", sql)
        self.assertIn("'DEV' ENVIRONMENT", sql)
        self.assertNotIn("P_PROJECT_CODE", sql)
        self.assertNotIn("P_ENVIRONMENT", sql)

    def test_checkpoint_and_runs_use_current_generation(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("target.GENERATION = source.GENERATION", sql)
        self.assertIn(":V_GENERATION AS GENERATION", sql)
        self.assertIn("dataset reset is in progress", sql)
        self.assertIn("STATE = 'READY_FOR_INITIAL_LOAD'", sql)
        self.assertIn("SET STATUS = 'COMPLETED'", sql)

    def test_grants_only_surface_access_to_domain_deploy_roles(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("GRANT SELECT ON VIEW PLATFORM_CONTROL.OPERATIONS.HEALTH_PIPELINE_RUN TO ROLE AR_HEALTH_DEPLOY;", sql)
        self.assertIn("GRANT USAGE ON PROCEDURE PLATFORM_CONTROL.OPERATIONS.TRANSPORT_PIPELINE_RUN_START", sql)
        self.assertNotIn("GRANT SELECT ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_", sql)
        self.assertNotIn("GRANT INSERT ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_", sql)
        self.assertNotIn("GRANT UPDATE ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_", sql)
        self.assertNotIn("GRANT DELETE ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_", sql)

    def test_finish_update_is_domain_and_environment_scoped(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("AND PROJECT_CODE = 'HEALTH'", sql)
        self.assertIn("AND ENVIRONMENT = 'DEV'", sql)
        self.assertIn("AND PROJECT_CODE = 'TRANSPORT'", sql)

    def test_rejects_invalid_identifier(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.render({"environment": "dev", "projects": {"bad": {"code": "HEALTH; DROP DATABASE PROD"}}})

    def test_rejects_unknown_environment(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.render({"environment": "sandbox", "projects": {"health": {"code": "HEALTH"}}})


if __name__ == "__main__":
    unittest.main()
