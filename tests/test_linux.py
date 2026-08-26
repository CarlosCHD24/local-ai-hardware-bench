from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from local_ai_bench.system.detect import detect_backend, doctor_checks
from local_ai_bench.system.linux import _cpu_model, _memory_bytes, _nvidia_gpus, _os_release


class LinuxTests(unittest.TestCase):
    def test_parses_linux_system_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            os_release = root / "os-release"
            cpuinfo = root / "cpuinfo"
            meminfo = root / "meminfo"
            os_release.write_text('NAME="Ubuntu"\nPRETTY_NAME="Ubuntu 24.04 LTS"\nID=ubuntu\n')
            cpuinfo.write_text("processor: 0\nmodel name: AMD Ryzen 5 5400H\n")
            meminfo.write_text("MemTotal:       32768000 kB\n")

            self.assertEqual(_os_release(os_release)["ID"], "ubuntu")
            self.assertEqual(_cpu_model(cpuinfo), "AMD Ryzen 5 5400H")
            self.assertEqual(_memory_bytes(meminfo), 32768000 * 1024)

    @patch("local_ai_bench.system.linux.command_output")
    def test_parses_nvidia_gpu(self, command_output) -> None:
        command_output.return_value = "NVIDIA GeForce RTX 4070, 16376, 590.10"

        devices = _nvidia_gpus()

        self.assertEqual(devices[0]["vendor"], "NVIDIA")
        self.assertEqual(devices[0]["memory_bytes"], 16376 * 1024 * 1024)
        self.assertEqual(devices[0]["driver"], "590.10")

    @patch("local_ai_bench.system.detect.shutil.which")
    @patch("local_ai_bench.system.detect.platform.system", return_value="Linux")
    def test_auto_selects_cuda_only_with_nvcc(self, system, which) -> None:
        which.side_effect = lambda name: f"/usr/bin/{name}" if name in {"nvcc", "nvidia-smi"} else None
        self.assertEqual(detect_backend(), "cuda")

        which.side_effect = lambda name: "/usr/bin/nvidia-smi" if name == "nvidia-smi" else None
        self.assertEqual(detect_backend(), "cpu")

    @patch("local_ai_bench.system.detect.shutil.which")
    @patch("local_ai_bench.system.detect.platform.system", return_value="Linux")
    def test_cuda_doctor_requires_toolkit_and_driver_tools(self, system, which) -> None:
        which.side_effect = lambda name: None if name == "nvidia-smi" else f"/usr/bin/{name}"

        checks = {check["name"]: check for check in doctor_checks("cuda")}

        self.assertTrue(checks["nvcc"]["ok"])
        self.assertFalse(checks["nvidia-smi"]["ok"])


if __name__ == "__main__":
    unittest.main()
