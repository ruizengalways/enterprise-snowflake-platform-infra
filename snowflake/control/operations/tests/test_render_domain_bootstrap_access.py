from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "render_domain_bootstrap_access.py"
SPEC = importlib.util.spec_from_file_location("render_domain_bootstrap_access", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RenderDomainBootstrapAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "environment": "dev",
            "projects": {
                "health": {"code": "HEALTH"},
                "transport": {"code": "TRANSPORT"},
            },
        }

    def test_view_is_domain_environment_and_current_generation_scoped(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("HEALTH_PIPELINE_BOOTSTRAP", sql)
        self.assertIn("bootstrap.PROJECT_CODE = 'HEALTH'", sql)
        self.assertIn("bootstrap.ENVIRONMENT = 'DEV'", sql)
        self.assertIn("bootstrap.GENERATION = COALESCE(lifecycle.CURRENT_GENERATION, 1)", sql)

    def test_write_api_fixes_domain_and_environment_server_side(self) -> None:
        sql = MODULE.render(self.config)
        for operation in (
            "PIPELINE_BOOTSTRAP_START",
            "PIPELINE_BOOTSTRAP_MARK_SNAPSHOT_LANDED",
            "PIPELINE_BOOTSTRAP_MARK_VALIDATED",
            "PIPELINE_BOOTSTRAP_COMMIT_HANDOFF",
        ):
            self.assertIn(f"PLATFORM_CONTROL.OPERATIONS.HEALTH_{operation}", sql)
        self.assertNotIn("P_PROJECT_CODE", sql)
        self.assertNotIn("P_ENVIRONMENT", sql)

    def test_state_machine_is_fail_closed_and_retry_safe(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("'BOUNDARY_CAPTURED'", sql)
        self.assertIn("'SNAPSHOT_LANDED'", sql)
        self.assertIn("'SNAPSHOT_VALIDATED'", sql)
        self.assertIn("'HANDOFF_COMMITTED'", sql)
        self.assertIn("bootstrap already started", sql)
        self.assertIn("snapshot already recorded", sql)
        self.assertIn("bootstrap already validated", sql)
        self.assertIn("bootstrap handoff already committed", sql)
        self.assertIn("dataset reset is in progress", sql)

    def test_validation_requires_explicit_pass_and_audit_details(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("P_RECONCILIATION_PASSED IS NULL OR NOT P_RECONCILIATION_PASSED", sql)
        self.assertIn("reconciliation details are required", sql)
        self.assertIn("RECONCILIATION_PASSED = :P_RECONCILIATION_PASSED", sql)

    def test_initial_bootstrap_rejects_only_current_generation_checkpoint(self) -> None:
        sql = MODULE.render(self.config)
        start = sql.index("HEALTH_PIPELINE_BOOTSTRAP_START")
        end = sql.index("$$;", start)
        procedure = sql[start:end]
        self.assertIn("FROM PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT", procedure)
        self.assertIn("GENERATION = :V_GENERATION", procedure)
        self.assertIn("initial bootstrap cannot start after current-generation checkpoint exists", procedure)

    def test_handoff_commit_is_atomic_generation_aware_and_cannot_rewind(self) -> None:
        sql = MODULE.render(self.config)
        start = sql.index("HEALTH_PIPELINE_BOOTSTRAP_COMMIT_HANDOFF")
        end = sql.index("$$;", start)
        procedure = sql[start:end]
        self.assertIn("BEGIN TRANSACTION;", procedure)
        self.assertIn("GENERATION = :V_GENERATION", procedure)
        self.assertIn("NOT EQUAL_NULL(CHECKPOINT_VALUE, :V_POSITION)", procedure)
        self.assertIn("MERGE INTO PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT", procedure)
        self.assertIn("SET STATUS = 'HANDOFF_COMMITTED'", procedure)
        self.assertIn("STATE = 'ACTIVE'", procedure)
        self.assertIn("STATUS = 'COMPLETED'", procedure)
        self.assertIn("COMMIT;", procedure)
        self.assertIn("ROLLBACK", procedure)

    def test_grants_expose_only_domain_surface(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn("HEALTH_PIPELINE_BOOTSTRAP TO ROLE AR_HEALTH_DEPLOY", sql)
        self.assertIn("TRANSPORT_PIPELINE_BOOTSTRAP_MARK_VALIDATED(VARCHAR, VARCHAR, BOOLEAN, VARIANT)", sql)
        self.assertNotIn("GRANT UPDATE ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP", sql)

    def test_rejects_invalid_identifier_and_environment(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.render({"environment": "dev", "projects": {"bad": {"code": "HEALTH; DROP DATABASE PROD"}}})
        with self.assertRaises(ValueError):
            MODULE.render({"environment": "sandbox", "projects": {"health": {"code": "HEALTH"}}})


if __name__ == "__main__":
    unittest.main()
