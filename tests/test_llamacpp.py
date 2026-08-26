from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from local_ai_bench.runtimes.llamacpp import LlamaCppRuntime


ROOT = Path(__file__).resolve().parents[1]


class LlamaCppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_config = {
            "repository": "https://example.invalid/llama.cpp.git",
            "revision": "a" * 40,
            "binary": "llama-bench",
            "gpu_layers": 99,
        }

    def test_parse_json_fixture(self) -> None:
        with TemporaryDirectory() as directory:
            binary = Path(directory) / "llama-bench"
            binary.touch()
            runtime = LlamaCppRuntime(self.runtime_config, Path(directory), "metal", binary)
            output = (ROOT / "tests" / "fixtures" / "llama_bench.json").read_text()
            records = runtime.parse(output)
            self.assertEqual(records[0]["avg_ts"], 64.0)
            self.assertEqual(records[0]["backend"], "Metal")

    def test_command_uses_cpu_without_offload(self) -> None:
        with TemporaryDirectory() as directory:
            binary = Path(directory) / "llama-bench"
            binary.touch()
            runtime = LlamaCppRuntime(self.runtime_config, Path(directory), "cpu", binary)
            command = runtime.command(
                Path("model.gguf"),
                {"prompt_tokens": 512, "generated_tokens": 0},
                repetitions=5,
                threads=6,
            )
            self.assertIn("json", command)
            self.assertEqual(command[command.index("-ngl") + 1], "0")
            self.assertEqual(command[command.index("-t") + 1], "6")

    def test_auto_fit_profile_omits_fixed_gpu_layers(self) -> None:
        with TemporaryDirectory() as directory:
            binary = Path(directory) / "llama-bench"
            binary.touch()
            runtime = LlamaCppRuntime(self.runtime_config, Path(directory), "metal", binary)
            command = runtime.command(
                Path("model.gguf"),
                {"prompt_tokens": 0, "generated_tokens": 32},
                repetitions=3,
                profile={"fit_target_mib": 1024, "fit_context": 4096, "verbose": True},
            )
            self.assertNotIn("-ngl", command)
            self.assertEqual(command[command.index("-fitt") + 1], "1024")
            self.assertEqual(command[command.index("-fitc") + 1], "4096")
            self.assertIn("-v", command)

    def test_cuda_unified_memory_is_scoped_to_cuda(self) -> None:
        with TemporaryDirectory() as directory:
            binary = Path(directory) / "llama-bench"
            binary.touch()
            cuda = LlamaCppRuntime(self.runtime_config, Path(directory), "cuda", binary)
            cpu = LlamaCppRuntime(self.runtime_config, Path(directory), "cpu", binary)
            profile = {"cuda_unified_memory": True}

            self.assertEqual(cuda.environment(profile)["GGML_CUDA_ENABLE_UNIFIED_MEMORY"], "1")
            self.assertNotIn("GGML_CUDA_ENABLE_UNIFIED_MEMORY", cpu.environment(profile))


if __name__ == "__main__":
    unittest.main()
