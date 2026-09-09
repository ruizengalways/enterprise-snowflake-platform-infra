from __future__ import annotations

import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
EXPECTED_STABLE_SCHEMAS = {
    "BRONZE",
    "SILVER_STAGING",
    "SILVER_INTERMEDIATE",
    "SILVER_CANONICAL",
    "GOLD_MARTS",
    "GOLD_SEMANTIC",
    "DQ",
}
EXPECTED_PUBLISHED_SCHEMAS = {"GOLD_MARTS", "GOLD_SEMANTIC"}
LEGACY_SCHEMAS = {"STAGING", "INTERMEDIATE", "CANONICAL", "MARTS", "SEMANTIC"}


class MedallionEnvironmentConfigTests(unittest.TestCase):
    def test_stable_domain_databases_use_one_medallion_schema_contract(self) -> None:
        for environment in ("dev", "uat", "prod"):
            path = REPO_ROOT / "config" / "environments" / f"{environment}.yml"
            config = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertIn("CONFIG", config["platform_control"]["schemas"])

            for database in config["analytics_databases"].values():
                name = database["name"]
                schemas = set(database["schemas"])
                published = set(database["published_schemas"])
                if name.startswith("CI_"):
                    self.assertEqual(set(), schemas)
                    self.assertEqual(set(), published)
                    continue

                self.assertEqual(EXPECTED_STABLE_SCHEMAS, schemas, name)
                self.assertEqual(EXPECTED_PUBLISHED_SCHEMAS, published, name)
                self.assertTrue(schemas.isdisjoint(LEGACY_SCHEMAS), name)


if __name__ == "__main__":
    unittest.main()
