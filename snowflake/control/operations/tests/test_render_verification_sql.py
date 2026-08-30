from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "render_verification_sql.py"
SPEC = importlib.util.spec_from_file_location("render_verification_sql", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RenderVerificationSqlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "environment": "dev",
            "projects": {
                "health": {"code": "HEALTH"},
                "transport": {"code": "TRANSPORT"},
            },
        }

    def test_verifies_normal_and_bootstrap_objects_for_each_domain(self) -> None:
        sql = MODULE.render(self.config)
        expected = (
            "HEALTH_PIPELINE_CHECKPOINT",
            "HEALTH_PIPELINE_BOOTSTRAP",
            "HEALTH_PIPELINE_RUN_START",
            "HEALTH_PIPELINE_BOOTSTRAP_COMMIT_HANDOFF",
            "TRANSPORT_PIPELINE_CHECKPOINT",
            "TRANSPORT_PIPELINE_BOOTSTRAP",
            "TRANSPORT_PIPELINE_RUN_START",
            "TRANSPORT_PIPELINE_BOOTSTRAP_COMMIT_HANDOFF",
        )
        for name in expected:
            self.assertIn(name, sql)
        self.assertIn("PLATFORM_CONTROL.INFORMATION_SCHEMA.VIEWS", sql)
        self.assertIn("PLATFORM_CONTROL.INFORMATION_SCHEMA.PROCEDURES", sql)

    def test_verifies_project_role_view_and_procedure_grants(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("GRANTEE = 'AR_HEALTH_DEPLOY'", sql)
        self.assertIn("OBJECT_TYPE = 'VIEW'", sql)
        self.assertIn("PRIVILEGE_TYPE = 'SELECT'", sql)
        self.assertIn("OBJECT_TYPE = 'PROCEDURE'", sql)
        self.assertIn("PRIVILEGE_TYPE = 'USAGE'", sql)
        self.assertIn("RAISE E_GRANT_MISSING", sql)

    def test_rejects_direct_project_grants_on_shared_base_tables(self) -> None:
        sql = MODULE.render(self.config)
        for name in MODULE._SHARED_BASE_TABLES:
            self.assertIn(f"'{name}'", sql)
        self.assertIn("PRIVILEGE_TYPE IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES')", sql)
        self.assertIn("RAISE E_FORBIDDEN_GRANT", sql)

    def test_environment_and_project_codes_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.render({"environment": "sandbox", "projects": {"health": {"code": "HEALTH"}}})
        with self.assertRaises(ValueError):
            MODULE.render({"environment": "dev", "projects": {"bad": {"code": "bad-role;drop"}}})


if __name__ == "__main__":
    unittest.main()
