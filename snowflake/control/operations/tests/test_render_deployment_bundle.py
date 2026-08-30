from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "render_deployment_bundle.py"
SPEC = importlib.util.spec_from_file_location("render_deployment_bundle", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RenderDeploymentBundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "environment": "dev",
            "projects": {
                "health": {"code": "HEALTH"},
                "transport": {"code": "TRANSPORT"},
            },
        }

    def test_bundle_preserves_base_dependency_order(self) -> None:
        sql = MODULE.render_bundle(self.config)
        markers = [f"-- BEGIN BASE: {name}" for name in MODULE.BASE_SQL_FILES]
        positions = [sql.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(
            sql.index("-- BEGIN BASE: pipeline_checkpoint.sql"),
            sql.index("-- BEGIN BASE: pipeline_bootstrap.sql"),
        )
        self.assertLess(
            sql.index("-- BEGIN BASE: pipeline_bootstrap.sql"),
            sql.index("-- BEGIN GENERATED: bootstrap handoff access"),
        )

    def test_bundle_contains_both_domain_surface_families(self) -> None:
        sql = MODULE.render_bundle(self.config)
        self.assertIn("HEALTH_PIPELINE_CHECKPOINT", sql)
        self.assertIn("TRANSPORT_PIPELINE_RUN_START", sql)
        self.assertIn("HEALTH_PIPELINE_BOOTSTRAP", sql)
        self.assertIn("TRANSPORT_PIPELINE_BOOTSTRAP_COMMIT_HANDOFF", sql)
        self.assertIn("P_RECONCILIATION_PASSED BOOLEAN", sql)

    def test_bundle_keeps_project_roles_off_shared_base_tables(self) -> None:
        sql = MODULE.render_bundle(self.config).upper()
        forbidden = (
            "GRANT SELECT ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_",
            "GRANT INSERT ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_",
            "GRANT UPDATE ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_",
            "GRANT DELETE ON TABLE PLATFORM_CONTROL.OPERATIONS.PIPELINE_",
        )
        for text in forbidden:
            self.assertNotIn(text, sql)

    def test_missing_base_sql_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                MODULE.render_bundle(self.config, Path(tmp))


if __name__ == "__main__":
    unittest.main()
