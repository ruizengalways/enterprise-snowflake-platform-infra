from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "render_domain_reset_access.py"
SPEC = importlib.util.spec_from_file_location("render_domain_reset_access", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RenderDomainResetAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "environment": "dev",
            "projects": {
                "health": {"code": "HEALTH"},
                "transport": {"code": "TRANSPORT"},
            },
        }

    def test_reset_is_domain_scoped_and_generation_based(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("HEALTH_DATASET_LIFECYCLE", sql)
        self.assertIn("HEALTH_DATASET_RESET_START", sql)
        self.assertIn("HEALTH_DATASET_RESET_COMPLETE", sql)
        self.assertIn("CURRENT_GENERATION", sql)
        self.assertIn("V_GENERATION + 1", sql)
        self.assertIn("'RESETTING'", sql)
        self.assertIn("'READY_FOR_INITIAL_LOAD'", sql)
        self.assertNotIn("P_PROJECT_CODE", sql)
        self.assertNotIn("P_ENVIRONMENT", sql)

    def test_reset_rejects_running_pipeline_and_preserves_old_state(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("STATUS = 'RUNNING'", sql)
        self.assertIn("cannot reset while a current-generation pipeline run is RUNNING", sql)
        self.assertNotIn("DELETE FROM PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT", sql.upper())
        self.assertNotIn("DELETE FROM PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP", sql.upper())

    def test_recovery_role_only_gets_domain_views_and_procedures(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("TO ROLE AR_HEALTH_RECOVERY", sql)
        self.assertIn("TO ROLE AR_TRANSPORT_RECOVERY", sql)
        self.assertNotIn("GRANT DELETE ON TABLE", sql.upper())
        self.assertNotIn("GRANT TRUNCATE ON TABLE", sql.upper())
        self.assertNotIn("GRANT UPDATE ON TABLE", sql.upper())

    def test_rejects_invalid_identifier_and_environment(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.render({"environment": "dev", "projects": {"bad": {"code": "X; DROP DATABASE Y"}}})
        with self.assertRaises(ValueError):
            MODULE.render({"environment": "sandbox", "projects": {"health": {"code": "HEALTH"}}})


if __name__ == "__main__":
    unittest.main()
