from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from local_ai_bench.memory import (
    MIB,
    MemorySampler,
    _amdgpu_snapshot,
    _linux_process_group_pids,
    _linux_process_memory,
    _nvidia_process_memory,
    classify_pressure,
    summarize_samples,
)


class MemoryTests(unittest.TestCase):
    def test_summarizes_swap_and_compression_growth(self) -> None:
        summary = summarize_samples(
            [
                {"swap_used_bytes": 0, "compressed_bytes": 100 * MIB, "available_percent": 50, "swapouts": 2},
                {
                    "swap_used_bytes": 512 * MIB,
                    "compressed_bytes": 500 * MIB,
                    "available_percent": 12,
                    "swapouts": 5,
                    "process_rss_bytes": 2 * MIB,
                    "process_swap_bytes": MIB,
                    "process_device_memory_used_bytes": 3 * MIB,
                    "amdgpu_vram_used_bytes": 96 * MIB,
                    "amdgpu_gtt_used_bytes": 384 * MIB,
                    "amdgpu_gpu_busy_percent": 87,
                },
            ],
            None,
            1000,
        )
        self.assertEqual(summary["swap_growth_bytes"], 512 * MIB)
        self.assertEqual(summary["compressed_growth_bytes"], 400 * MIB)
        self.assertEqual(summary["available_percent_min"], 12)
        self.assertEqual(summary["peak_process_rss_bytes"], 2 * MIB)
        self.assertEqual(summary["peak_process_swap_bytes"], MIB)
        self.assertEqual(summary["peak_process_device_memory_used_bytes"], 3 * MIB)
        self.assertEqual(summary["peak_amdgpu_vram_used_bytes"], 96 * MIB)
        self.assertEqual(summary["peak_amdgpu_gtt_used_bytes"], 384 * MIB)
        self.assertEqual(summary["peak_amdgpu_gpu_busy_percent"], 87)
        self.assertEqual(classify_pressure(summary, "ok"), "swapping")

    def test_pressure_abort_takes_precedence(self) -> None:
        self.assertEqual(classify_pressure({"abort_reason": "limit"}, "aborted_pressure"), "aborted")

    def test_reports_resident_swap_without_new_swapouts(self) -> None:
        memory = {"swap_used_before_bytes": 512 * MIB, "swap_growth_bytes": 0, "swapouts_delta": 0}
        self.assertEqual(classify_pressure(memory, "ok"), "swap_resident")

    @patch("local_ai_bench.memory.os.killpg")
    def test_pressure_abort_kills_the_process_group(self, killpg) -> None:
        sampler = MemorySampler(1234)

        sampler._abort("swap_growth_exceeded")

        killpg.assert_called_once_with(1234, 9)
        self.assertEqual(sampler.abort_reason, "swap_growth_exceeded")

    def test_reads_linux_process_group_memory(self) -> None:
        with TemporaryDirectory() as directory:
            proc_root = Path(directory)
            for pid, group, rss, swap in ((101, 77, 2048, 32), (102, 77, 1024, 0), (103, 88, 9999, 9999)):
                process = proc_root / str(pid)
                process.mkdir()
                (process / "stat").write_text(
                    f"{pid} (llama bench) R 1 {group} 0 0 0\n", encoding="utf-8"
                )
                (process / "status").write_text(
                    f"Name:\tllama-bench\nVmRSS:\t{rss} kB\nVmSwap:\t{swap} kB\n",
                    encoding="utf-8",
                )

            process_ids = _linux_process_group_pids(77, proc_root)
            rss_bytes, swap_bytes = _linux_process_memory(process_ids, proc_root)

            self.assertEqual(process_ids, {101, 102})
            self.assertEqual(rss_bytes, 3072 * 1024)
            self.assertEqual(swap_bytes, 32 * 1024)

    def test_reads_amdgpu_sysfs_metrics(self) -> None:
        with TemporaryDirectory() as directory:
            drm_root = Path(directory)
            device = drm_root / "card0" / "device"
            device.mkdir(parents=True)
            (device / "uevent").write_text("DRIVER=amdgpu\n", encoding="utf-8")
            values = {
                "mem_info_vram_used": 128 * MIB,
                "mem_info_vram_total": 512 * MIB,
                "mem_info_gtt_used": 768 * MIB,
                "mem_info_gtt_total": 8 * 1024 * MIB,
                "gpu_busy_percent": 73,
            }
            for name, value in values.items():
                (device / name).write_text(str(value), encoding="utf-8")

            snapshot = _amdgpu_snapshot(drm_root)

            self.assertEqual(snapshot["amdgpu_device_count"], 1)
            self.assertEqual(snapshot["amdgpu_vram_used_bytes"], 128 * MIB)
            self.assertEqual(snapshot["amdgpu_gtt_used_bytes"], 768 * MIB)
            self.assertEqual(snapshot["amdgpu_gpu_busy_percent"], 73)

    @patch("local_ai_bench.memory._command")
    def test_attributes_nvidia_memory_to_process_group(self, command) -> None:
        command.return_value = "101, 512\n202, 2048\n102, 256\n"

        self.assertEqual(_nvidia_process_memory({101, 102}), 768 * MIB)


if __name__ == "__main__":
    unittest.main()
