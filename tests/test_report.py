from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from local_ai_bench.report import compare_runs, write_report
from local_ai_bench.validate import validate_result_dir


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def make_run(root: Path, system_id: str, speed: float) -> Path:
    run = root / system_id
    (run / "raw").mkdir(parents=True)
    (run / "raw" / "sample.json").write_text("[]", encoding="utf-8")
    write_json(
        run / "manifest.json",
        {
            "suite": {"id": "quick-v1"},
            "models": [
                {
                    "id": "model-a",
                    "revision": "a" * 40,
                    "artifacts": [{"filename": "model.gguf", "sha256": "b" * 64}],
                }
            ],
        },
    )
    write_json(
        run / "system.json",
        {
            "system_id": system_id,
            "cpu": {"model": "Fixture CPU"},
            "memory": {"total_bytes": 16 * 1024**3},
        },
    )
    write_json(
        run / "results.json",
        {
            "schema_version": 1,
            "suite": {"id": "quick-v1", "schema_version": 1},
            "system_id": system_id,
            "run_id": "fixture",
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:01:00Z",
            "runtime": {"backend": "cpu"},
            "models": [{"id": "model-a"}],
            "results": [
                {
                    "model_id": "model-a",
                    "scenario_id": "tg128",
                    "status": "ok",
                    "metrics": {
                        "tokens_per_second_mean": speed,
                        "tokens_per_second_stddev": 0.5,
                    },
                    "runtime_details": {"backend": "CPU", "n_threads": 8, "n_gpu_layers": 0},
                    "raw_file": "raw/sample.json",
                    "error": None,
                }
            ],
        },
    )
    return run


class ReportTests(unittest.TestCase):
    def test_validate_report_and_compare(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = make_run(root, "system-a", 20.0)
            second = make_run(root, "system-b", 40.0)
            self.assertEqual(validate_result_dir(first)["results"]["system_id"], "system-a")
            report, csv_path = write_report(first)
            self.assertIn("20.00", report.read_text())
            self.assertIn("tokens_per_second_mean", csv_path.read_text())
            comparison = compare_runs([first, second])
            self.assertIn("system-a", comparison)
            self.assertIn("40.00", comparison)

    def test_report_falls_back_to_configured_backend(self) -> None:
        with TemporaryDirectory() as directory:
            run = make_run(Path(directory), "system-a", 20.0)
            data = json.loads((run / "results.json").read_text(encoding="utf-8"))
            data["runtime"]["backend"] = "metal"
            data["results"][0]["runtime_details"].pop("backend")
            write_json(run / "results.json", data)

            report, csv_path = write_report(run)

            self.assertIn("| metal |", report.read_text(encoding="utf-8"))
            self.assertIn(",metal,", csv_path.read_text(encoding="utf-8"))

    def test_compare_distinguishes_backends_and_unions_profiles(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            cpu = make_run(root / "cpu", "same-system", 20.0)
            vulkan = make_run(root / "vulkan", "same-system", 30.0)
            cpu_data = json.loads((cpu / "results.json").read_text(encoding="utf-8"))
            cpu_data["results"][0]["profile_id"] = "cpu-resident"
            write_json(cpu / "results.json", cpu_data)
            vulkan_data = json.loads((vulkan / "results.json").read_text(encoding="utf-8"))
            vulkan_data["runtime"]["backend"] = "vulkan"
            vulkan_data["results"][0]["profile_id"] = "auto-fit"
            write_json(vulkan / "results.json", vulkan_data)

            comparison = compare_runs([cpu, vulkan])

            self.assertIn("same-system [cpu]", comparison)
            self.assertIn("same-system [vulkan]", comparison)
            self.assertIn("cpu-resident", comparison)
            self.assertIn("auto-fit", comparison)

    def test_report_includes_linux_process_memory_and_cuda_spill_mode(self) -> None:
        with TemporaryDirectory() as directory:
            run = make_run(Path(directory), "linux-nvidia", 10.0)
            data = json.loads((run / "results.json").read_text(encoding="utf-8"))
            data["results"][0]["profile_id"] = "full-accelerator"
            data["results"][0]["memory"] = {
                "peak_process_rss_bytes": 4 * 1024**3,
                "peak_process_swap_bytes": 512 * 1024**2,
                "peak_process_device_memory_used_bytes": 15 * 1024**3,
                "available_memory_drop_bytes": 6 * 1024**3,
                "cuda_unified_memory_enabled": True,
                "placement": "gpu_full",
                "pressure": "normal",
            }
            write_json(run / "results.json", data)

            report, csv_path = write_report(run)
            report_text = report.read_text(encoding="utf-8")
            csv_text = csv_path.read_text(encoding="utf-8")

            self.assertIn("VRAM proceso", report_text)
            self.assertIn("| sí |", report_text)
            self.assertIn("peak_process_device_memory_used_bytes", csv_text)
            self.assertIn("cuda_unified_memory_enabled", csv_text)

    def test_report_includes_amdgpu_unified_memory_metrics(self) -> None:
        with TemporaryDirectory() as directory:
            run = make_run(Path(directory), "linux-amd-apu", 8.0)
            system = json.loads((run / "system.json").read_text(encoding="utf-8"))
            system["accelerators"] = [
                {
                    "name": "AMD Radeon Graphics",
                    "vulkan_name": "AMD Radeon Graphics (RADV RENOIR)",
                    "memory_architecture": "unified",
                }
            ]
            write_json(run / "system.json", system)
            data = json.loads((run / "results.json").read_text(encoding="utf-8"))
            data["runtime"]["backend"] = "vulkan"
            data["results"][0]["memory"] = {
                "amdgpu_vram_growth_bytes": 64 * 1024**2,
                "amdgpu_gtt_growth_bytes": 1024**3,
                "peak_amdgpu_gpu_busy_percent": 92,
                "memory_architecture": "unified",
                "spill_mode": "shared_memory_pressure",
                "placement": "unified_gpu",
                "pressure": "normal",
            }
            write_json(run / "results.json", data)

            report, csv_path = write_report(run)
            report_text = report.read_text(encoding="utf-8")
            csv_text = csv_path.read_text(encoding="utf-8")

            self.assertIn("AMD Radeon Graphics (RADV RENOIR) (unified)", report_text)
            self.assertIn("shared_memory_pressure", report_text)
            self.assertIn("92 %", report_text)
            self.assertIn("amdgpu_gtt_growth_bytes", csv_text)


if __name__ == "__main__":
    unittest.main()
