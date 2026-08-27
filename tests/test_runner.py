from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from local_ai_bench.config import load_config
from local_ai_bench.models import update_verify_cache
from local_ai_bench.runner import (
    _finish_memory_record,
    _failure_status,
    _parse_runtime_placement,
    _remaining_timeout,
    _success_record,
    execute_suite,
)
from local_ai_bench.runtimes.llamacpp import LlamaCppRuntime
from local_ai_bench.validate import validate_result_dir


class RunnerIntegrationTests(unittest.TestCase):
    def test_classifies_vulkan_allocation_failure_as_oom(self) -> None:
        self.assertEqual(
            _failure_status(1, "vkAllocateMemory: VK_ERROR_OUT_OF_DEVICE_MEMORY", {}),
            "oom",
        )

    @patch("local_ai_bench.runner.time.monotonic", return_value=125.0)
    def test_remaining_timeout_shares_model_budget(self, monotonic) -> None:
        self.assertEqual(_remaining_timeout(300, 200.0), 75.0)
        self.assertEqual(_remaining_timeout(300, 100.0), 0.0)
        self.assertEqual(_remaining_timeout(300, None), 300.0)

    def test_parses_actual_offload_and_buffer_placement(self) -> None:
        details = _parse_runtime_placement(
            "ggml_vulkan: 0 = AMD Radeon Graphics (RADV RENOIR) | uma: 1 | fp16: 1\n"
            "llama_model_load: offloaded 40/49 layers to GPU\n"
            "llama_model_load: MTL0_Mapped model buffer size = 8192.00 MiB\n"
            "llama_model_load: CPU_Mapped model buffer size = 512.00 MiB\n"
        )
        self.assertEqual(details["offloaded_layers"], 40)
        self.assertEqual(details["total_layers"], 49)
        self.assertEqual(details["device_model_bytes"], 8192 * 1024 * 1024)
        self.assertEqual(details["host_model_bytes"], 512 * 1024 * 1024)
        self.assertEqual(details["memory_architecture"], "unified")

    def test_classifies_full_vulkan_uma_as_shared_memory(self) -> None:
        memory = {}
        record = {
            "status": "ok",
            "runtime_details": {
                "offloaded_layers": 49,
                "total_layers": 49,
                "memory_architecture": "unified",
            },
        }

        _finish_memory_record(memory, record, "vulkan", {"layers": 49})

        self.assertEqual(memory["placement"], "unified_gpu")
        self.assertEqual(memory["memory_architecture"], "unified")
        self.assertEqual(memory["spill_mode"], "shared_memory_pressure")

    def test_normalizes_plural_llama_cpp_backends_field(self) -> None:
        record = _success_record(
            {"id": "fixture-model"},
            {"id": "tg8"},
            Path("raw.json"),
            [{"backends": "MTL,BLAS", "avg_ts": 42.0}],
        )

        self.assertEqual(record["runtime_details"]["backend"], "MTL,BLAS")

    def test_end_to_end_with_fake_llama_bench(self) -> None:
        with TemporaryDirectory() as directory_text:
            root = Path(directory_text)
            (root / "suites").mkdir()
            (root / "models").mkdir()
            home = root / "home"
            output = root / "results"
            content = b"tiny gguf fixture"
            digest = hashlib.sha256(content).hexdigest()
            model_id = "fixture-model"
            filename = "fixture.gguf"

            suite = {
                "schema_version": 1,
                "id": "fixture-v1",
                "runtime": {
                    "id": "llama.cpp",
                    "repository": "https://example.invalid/llama.cpp.git",
                    "revision": "a" * 40,
                    "binary": "llama-bench",
                    "gpu_layers": 99,
                },
                "model_manifest": "fixture.json",
                "models": [model_id],
                "profiles": [{"id": "test-profile", "gpu_layers": 0}],
                "scenarios": [{"id": "tg8", "prompt_tokens": 0, "generated_tokens": 8}],
                "repetitions": 2,
                "warmup_runs": 1,
                "timeout_seconds": 10,
                "memory_monitoring": {"interval_ms": 200},
            }
            model = {
                "id": model_id,
                "parameters_billions": 0.001,
                "repository": "fixture/repository",
                "revision": "b" * 40,
                "primary_artifact": filename,
                "artifacts": [
                    {
                        "filename": filename,
                        "url": "https://example.invalid/fixture.gguf",
                        "size_bytes": len(content),
                        "sha256": digest,
                    }
                ],
            }
            manifest = {
                "schema_version": 1,
                "id": "fixture",
                "family": "fixture",
                "quantization": "fixture",
                "license": "MIT",
                "models": [model],
            }
            (root / "suites" / "fixture-v1.json").write_text(json.dumps(suite))
            (root / "models" / "fixture.json").write_text(json.dumps(manifest))

            model_directory = home / "models" / model_id
            model_directory.mkdir(parents=True)
            (model_directory / filename).write_bytes(content)
            update_verify_cache(model_directory, model["artifacts"][0])

            binary = root / "fake-llama-bench"
            binary.write_text(
                "#!/usr/bin/env python3\n"
                "import json, sys\n"
                "if '--version' in sys.argv:\n"
                "    print('fake llama-bench 1.0')\n"
                "else:\n"
                "    print(json.dumps([{'backend': 'CPU', 'test': 'tg8', "
                "'avg_ts': 42.0, 'stddev_ts': 0.5, 'avg_ns': 10, 'stddev_ns': 1, "
                "'samples_ts': [41.5, 42.5], 'samples_ns': [11, 9], "
                "'n_threads': 4, 'n_gpu_layers': 0}]))\n"
            )
            binary.chmod(0o755)

            loaded = load_config("fixture-v1", root)
            runtime = LlamaCppRuntime(loaded.suite["runtime"], home, "cpu", binary)
            run_dir = execute_suite(
                loaded,
                runtime,
                home,
                output,
                "fixture-system",
                [model],
            )
            validated = validate_result_dir(run_dir)
            record = validated["results"]["results"][0]
            self.assertEqual(record["status"], "ok")
            self.assertEqual(record["profile_id"], "test-profile")
            self.assertEqual(record["metrics"]["tokens_per_second_mean"], 42.0)
            self.assertIn("peak_resident_memory_bytes", record["metrics"])
            self.assertEqual(record["memory"]["pressure"], "normal")
            self.assertTrue((run_dir / record["memory"]["samples_file"]).is_file())
            self.assertTrue((run_dir / "report.md").is_file())
            self.assertTrue((run_dir / "results.csv").is_file())


if __name__ == "__main__":
    unittest.main()
