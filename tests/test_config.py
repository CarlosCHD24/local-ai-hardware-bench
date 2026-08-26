from __future__ import annotations

import unittest
from pathlib import Path

from local_ai_bench.config import (
    ConfigError,
    load_config,
    selected_profiles,
    validate_suite,
    validate_system_id,
)


ROOT = Path(__file__).resolve().parents[1]


class ConfigTests(unittest.TestCase):
    def test_quick_suite_is_valid(self) -> None:
        loaded = load_config("quick-v1", ROOT)
        self.assertEqual(loaded.suite["id"], "quick-v1")
        self.assertEqual(len(loaded.suite["models"]), 3)
        self.assertEqual(len(loaded.models_by_id), 3)

    def test_capacity_suite_has_large_models_and_profiles(self) -> None:
        loaded = load_config("capacity-v1", ROOT)
        self.assertEqual(loaded.suite["models"], [
            "qwen2.5-14b-instruct-q4_k_m",
            "qwen2.5-32b-instruct-q4_k_m",
        ])
        self.assertEqual([profile["id"] for profile in selected_profiles(loaded.suite)], [
            "auto-fit",
            "full-accelerator",
        ])
        self.assertEqual(selected_profiles(loaded.suite, ["auto-fit"])[0]["fit_target_mib"], 1024)
        self.assertEqual(loaded.suite["timeout_seconds"], 300)
        self.assertEqual(loaded.suite["model_time_budget_seconds"], 300)
        self.assertTrue(loaded.suite["skip_remaining_after_capacity_failure"])
        self.assertTrue(selected_profiles(loaded.suite, ["full-accelerator"])[0]["cuda_unified_memory"])

    def test_rejects_invalid_model_time_budget(self) -> None:
        loaded = load_config("capacity-v1", ROOT)
        suite = dict(loaded.suite)
        suite["model_time_budget_seconds"] = 0

        with self.assertRaises(ConfigError):
            validate_suite(suite, loaded.manifest)

    def test_system_id_rejects_private_or_unsafe_values(self) -> None:
        with self.assertRaises(ConfigError):
            validate_system_id("my laptop/user")

    def test_system_id_accepts_public_alias(self) -> None:
        self.assertEqual(validate_system_id("macbook-m4-16gb"), "macbook-m4-16gb")


if __name__ == "__main__":
    unittest.main()
