from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from local_ai_bench.system.detect import detect_backend, doctor_checks
from local_ai_bench.system.linux import (
    _cpu_model,
    _memory_bytes,
    _nvidia_gpus,
    _os_release,
    vulkan_devices,
)


class LinuxTests(unittest.TestCase):
    def test_parses_linux_system_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            os_release = root / "os-release"
            cpuinfo = root / "cpuinfo"
            meminfo = root / "meminfo"
            os_release.write_text('NAME="Ubuntu"\nPRETTY_NAME="Ubuntu 24.04 LTS"\nID=ubuntu\n')
            cpuinfo.write_text("processor: 0\nmodel name: AMD Ryzen 5 5600H\n")
            meminfo.write_text("MemTotal:       16384000 kB\n")

            self.assertEqual(_os_release(os_release)["ID"], "ubuntu")
            self.assertEqual(_cpu_model(cpuinfo), "AMD Ryzen 5 5600H")
            self.assertEqual(_memory_bytes(meminfo), 16384000 * 1024)

    @patch("local_ai_bench.system.linux.command_output")
    def test_parses_nvidia_gpu(self, command_output) -> None:
        command_output.return_value = "NVIDIA GeForce RTX 3060, 12288, 590.10"

        devices = _nvidia_gpus()

        self.assertEqual(devices[0]["vendor"], "NVIDIA")
        self.assertEqual(devices[0]["name"], "NVIDIA GeForce RTX 3060")
        self.assertEqual(devices[0]["memory_bytes"], 12288 * 1024 * 1024)
        self.assertEqual(devices[0]["driver"], "590.10")

    def test_parses_amd_integrated_vulkan_device(self) -> None:
        devices = vulkan_devices(
            """Devices:
========
GPU0:
    deviceType = PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU
    deviceName = AMD Radeon Graphics (RADV RENOIR)
    driverName = radv
    driverInfo = Mesa 24.0.9
"""
        )

        self.assertEqual(devices[0]["vendor"], "AMD")
        self.assertEqual(devices[0]["memory_architecture"], "unified")
        self.assertFalse(devices[0]["software"])

    def test_marks_llvmpipe_as_software_vulkan(self) -> None:
        devices = vulkan_devices(
            """GPU0:
    deviceType = PHYSICAL_DEVICE_TYPE_CPU
    deviceName = llvmpipe (LLVM 19.1.7, 256 bits)
    driverName = llvmpipe
"""
        )

        self.assertTrue(devices[0]["software"])

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

    @patch("local_ai_bench.system.detect.linux.vulkan_devices")
    @patch("local_ai_bench.system.detect.shutil.which")
    @patch("local_ai_bench.system.detect.platform.system", return_value="Linux")
    def test_vulkan_doctor_rejects_software_device(self, system, which, devices) -> None:
        which.side_effect = lambda name: f"/usr/bin/{name}"
        devices.return_value = [
            {
                "name": "llvmpipe",
                "driver": "llvmpipe",
                "software": True,
                "memory_architecture": "dedicated",
            }
        ]

        checks = {check["name"]: check for check in doctor_checks("vulkan")}

        self.assertTrue(checks["vulkaninfo"]["ok"])
        self.assertFalse(checks["vulkan_hardware_device"]["ok"])
        self.assertIn("software", checks["vulkan_hardware_device"]["value"])

    @patch("local_ai_bench.system.detect.linux.vulkan_devices")
    @patch("local_ai_bench.system.detect.shutil.which")
    @patch("local_ai_bench.system.detect.platform.system", return_value="Linux")
    def test_vulkan_doctor_accepts_amd_uma_device(self, system, which, devices) -> None:
        which.side_effect = lambda name: f"/usr/bin/{name}"
        devices.return_value = [
            {
                "name": "AMD Radeon Graphics (RADV RENOIR)",
                "driver": "radv",
                "software": False,
                "memory_architecture": "unified",
            }
        ]

        checks = {check["name"]: check for check in doctor_checks("vulkan")}

        self.assertTrue(checks["vulkan_hardware_device"]["ok"])
        self.assertIn("unified", checks["vulkan_hardware_device"]["value"])


if __name__ == "__main__":
    unittest.main()
