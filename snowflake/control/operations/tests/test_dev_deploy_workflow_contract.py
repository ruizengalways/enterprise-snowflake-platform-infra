from __future__ import annotations

import unittest
from pathlib import Path


class DevDeployWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[4]
        cls.workflow = (
            cls.root / ".github" / "workflows" / "platform-control-sql-deploy-dev.yml"
        ).read_text(encoding="utf-8")

    def test_dev_deploy_renders_and_executes_complete_bundle(self) -> None:
        text = self.workflow
        self.assertIn("render_deployment_bundle.py", text)
        self.assertIn("--config config/environments/dev.yml", text)
        self.assertIn('PLATFORM_CONTROL_BUNDLE: /tmp/platform-control-dev.sql', text)
        self.assertIn('-f "${PLATFORM_CONTROL_BUNDLE}"', text)

        # The deployment must not regress to manually executing only a subset of
        # base SQL files while silently omitting generated domain surfaces.
        self.assertNotIn("-f snowflake/control/operations/pipeline_checkpoint.sql", text)
        self.assertNotIn("-f snowflake/control/operations/pipeline_run.sql", text)
        self.assertNotIn("-f snowflake/control/operations/pipeline_check_result.sql", text)
        self.assertNotIn("-f snowflake/control/operations/advance_pipeline_checkpoint.sql", text)

    def test_dev_deploy_fails_closed_if_control_family_is_missing(self) -> None:
        text = self.workflow
        for marker in (
            "-- BEGIN BASE: pipeline_checkpoint.sql",
            "-- BEGIN BASE: pipeline_bootstrap.sql",
            "-- BEGIN BASE: dataset_lifecycle.sql",
            "-- BEGIN BASE: dataset_reset.sql",
            "-- BEGIN BASE: dataset_config_snapshot.sql",
            "-- BEGIN GENERATED: normal domain operational access",
            "-- BEGIN GENERATED: bootstrap handoff access",
            "-- BEGIN GENERATED: dataset reset access",
            "-- BEGIN GENERATED: dataset config snapshot access",
            "HEALTH_DATASET_RESET_START",
            "TRANSPORT_DATASET_RESET_START",
            "HEALTH_REGISTER_DATASET_CONFIG_SNAPSHOT",
            "TRANSPORT_REGISTER_DATASET_CONFIG_SNAPSHOT",
        ):
            self.assertIn(marker, text)

    def test_dev_deploy_keeps_account_scoped_wif_guard(self) -> None:
        text = self.workflow
        self.assertIn("SNOWFLAKE_OIDC_AUDIENCE", text)
        self.assertIn("snowflakecomputing.com", text)
        self.assertIn("account-scoped Snowflake OIDC audience", text)
        self.assertIn("--authenticator WORKLOAD_IDENTITY", text)
        self.assertIn("--workload-identity-provider OIDC", text)

    def test_post_deploy_verifies_v2_state_and_domain_surfaces(self) -> None:
        text = self.workflow
        for value in (
            "PIPELINE_BOOTSTRAP",
            "DATASET_LIFECYCLE",
            "DATASET_RESET",
            "DATASET_CONFIG_SNAPSHOT",
            "show views like 'HEALTH_%'",
            "show views like 'TRANSPORT_%'",
            "show procedures like 'HEALTH_%'",
            "show procedures like 'TRANSPORT_%'",
        ):
            self.assertIn(value, text)


if __name__ == "__main__":
    unittest.main()
