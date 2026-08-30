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

    def test_view_is_domain_and_environment_scoped(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn(
            "CREATE OR REPLACE SECURE VIEW PLATFORM_CONTROL.OPERATIONS.HEALTH_PIPELINE_BOOTSTRAP",
            sql,
        )
        self.assertIn("WHERE PROJECT_CODE = 'HEALTH'", sql)
        self.assertIn("AND ENVIRONMENT = 'DEV';", sql)
        self.assertIn("WHERE PROJECT_CODE = 'TRANSPORT'", sql)

    def test_write_api_fixes_domain_and_environment_server_side(self) -> None:
        sql = MODULE.render(self.config)
        for operation in (
            "PIPELINE_BOOTSTRAP_START",
            "PIPELINE_BOOTSTRAP_MARK_SNAPSHOT_LANDED",
            "PIPELINE_BOOTSTRAP_MARK_VALIDATED",
            "PIPELINE_BOOTSTRAP_COMMIT_HANDOFF",
        ):
            self.assertIn(
                f"PLATFORM_CONTROL.OPERATIONS.HEALTH_{operation}",
                sql,
            )
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
        self.assertIn("RAISE E_INVALID_STATE", sql)

    def test_handoff_commit_is_atomic_with_checkpoint_write(self) -> None:
        sql = MODULE.render(self.config)
        commit_start = sql.index(
            "CREATE OR REPLACE PROCEDURE PLATFORM_CONTROL.OPERATIONS.HEALTH_PIPELINE_BOOTSTRAP_COMMIT_HANDOFF"
        )
        commit_end = sql.index("$$;", commit_start)
        procedure = sql[commit_start:commit_end]
        self.assertIn("BEGIN TRANSACTION;", procedure)
        self.assertIn("MERGE INTO PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT", procedure)
        self.assertIn("SET STATUS = 'HANDOFF_COMMITTED'", procedure)
        self.assertIn("COMMIT;", procedure)
        self.assertIn("WHEN OTHER THEN", procedure)
        self.assertIn("ROLLBACK;", procedure)
        self.assertLess(
            procedure.index("MERGE INTO PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT"),
            procedure.index("SET STATUS = 'HANDOFF_COMMITTED'"),
        )

    def test_grants_expose_only_generated_domain_surface(self) -> None:
        sql = MODULE.render(self.config)
        self.assertIn(
            "GRANT SELECT ON VIEW PLATFORM_CONTROL.OPERATIONS.HEALTH_PIPELINE_BOOTSTRAP TO ROLE AR_HEALTH_DEPLOY;",
            sql,
        )
        self.assertIn(
            "GRANT USAGE ON PROCEDURE PLATFORM_CONTROL.OPERATIONS.TRANSPORT_PIPELINE_BOOTSTRAP_COMMIT_HANDOFF",
            sql,
        )
        self.assertNotIn("GRANT SELECT ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP", sql)
        self.assertNotIn("GRANT INSERT ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP", sql)
        self.assertNotIn("GRANT UPDATE ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP", sql)
        self.assertNotIn("GRANT DELETE ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_BOOTSTRAP", sql)
        self.assertNotIn("GRANT UPDATE ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_CHECKPOINT", sql)

    def test_rejects_invalid_identifier_and_environment(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.render(
                {
                    "environment": "dev",
                    "projects": {"bad": {"code": "HEALTH; DROP DATABASE PROD"}},
                }
            )
        with self.assertRaises(ValueError):
            MODULE.render(
                {"environment": "sandbox", "projects": {"health": {"code": "HEALTH"}}}
            )


if __name__ == "__main__":
    unittest.main()
