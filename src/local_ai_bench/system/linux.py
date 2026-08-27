from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import base_system, command_output


def _os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


def _cpu_model(path: Path = Path("/proc/cpuinfo")) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.lower().startswith("model name") and ":" in line:
            return line.split(":", 1)[1].strip()
    return None


def _memory_bytes(path: Path = Path("/proc/meminfo")) -> int | None:
    if not path.exists():
        return None
    match = re.search(r"^MemTotal:\s+(\d+)\s+kB", path.read_text(), re.MULTILINE)
    return int(match.group(1)) * 1024 if match else None


def _nvidia_gpus() -> list[dict[str, Any]]:
    output = command_output(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader,nounits",
        ]
    )
    if not output:
        return []
    devices: list[dict[str, Any]] = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) == 3:
            try:
                memory_bytes = int(float(parts[1]) * 1024 * 1024)
            except ValueError:
                continue
            devices.append(
                {
                    "kind": "gpu",
                    "vendor": "NVIDIA",
                    "name": parts[0],
                    "memory_bytes": memory_bytes,
                    "driver": parts[2],
                }
            )
    return devices


def _pci_accelerators() -> list[dict[str, Any]]:
    output = command_output(["lspci"])
    if not output:
        return []
    devices: list[dict[str, Any]] = []
    for line in output.splitlines():
        lower = line.lower()
        if "vga compatible controller" not in lower and "display controller" not in lower:
            continue
        if "amd" in lower or "ati" in lower:
            vendor = "AMD"
        elif "intel" in lower:
            vendor = "Intel"
        elif "nvidia" in lower:
            vendor = "NVIDIA"
        else:
            vendor = "unknown"
        devices.append({"kind": "gpu", "vendor": vendor, "name": line.split(": ", 1)[-1]})
    return devices


def vulkan_devices(summary: str | None = None) -> list[dict[str, Any]]:
    output = summary if summary is not None else command_output(["vulkaninfo", "--summary"])
    if not output:
        return []
    devices: list[dict[str, Any]] = []
    blocks = re.split(r"(?m)^\s*GPU\d+:\s*$", output)[1:]
    for block in blocks:
        fields = {
            key: value.strip()
            for key, value in re.findall(
                r"(?m)^\s*(deviceName|deviceType|driverName|driverInfo)\s*=\s*(.+?)\s*$",
                block,
            )
        }
        name = fields.get("deviceName")
        if not name:
            continue
        device_type = fields.get("deviceType", "unknown").lower()
        device_type = device_type.removeprefix("physical_device_type_")
        lower = " ".join(
            (name, fields.get("driverName", ""), fields.get("driverInfo", ""))
        ).lower()
        software = device_type == "cpu" or any(
            marker in lower for marker in ("llvmpipe", "lavapipe", "software rasterizer")
        )
        if "amd" in lower or "radeon" in lower or "radv" in lower:
            vendor = "AMD"
        elif "nvidia" in lower:
            vendor = "NVIDIA"
        elif "intel" in lower:
            vendor = "Intel"
        else:
            vendor = "unknown"
        integrated = device_type == "integrated_gpu"
        devices.append(
            {
                "name": name,
                "vendor": vendor,
                "device_type": device_type,
                "driver": fields.get("driverName"),
                "driver_info": fields.get("driverInfo"),
                "software": software,
                "memory_architecture": "unified" if integrated else "dedicated",
            }
        )
    return devices


def _enrich_accelerators_with_vulkan(
    accelerators: list[dict[str, Any]], devices: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    hardware_devices = [device for device in devices if not device["software"]]
    matched_accelerators: set[int] = set()
    for device in hardware_devices:
        match_index = next(
            (
                index
                for index, accelerator in enumerate(accelerators)
                if index not in matched_accelerators
                and accelerator.get("vendor") == device["vendor"]
            ),
            None,
        )
        metadata = {
            "vulkan_name": device["name"],
            "vulkan_device_type": device["device_type"],
            "vulkan_driver": device.get("driver"),
            "memory_architecture": device["memory_architecture"],
        }
        if match_index is not None:
            accelerators[match_index].update(metadata)
            matched_accelerators.add(match_index)
        else:
            accelerators.append(
                {"kind": "gpu", "vendor": device["vendor"], "name": device["name"], **metadata}
            )
    return accelerators


def collect(system_id: str) -> dict[str, Any]:
    data = base_system(system_id)
    release = _os_release()
    data["platform"].update(
        {
            "distribution": release.get("PRETTY_NAME", release.get("NAME", "unknown")),
            "distribution_id": release.get("ID"),
        }
    )
    data["cpu"]["model"] = _cpu_model() or data["cpu"]["model"]
    physical = command_output(["lscpu", "-p=SOCKET,CORE"])
    if physical:
        cores = {line for line in physical.splitlines() if line and not line.startswith("#")}
        data["cpu"]["physical_cores"] = len(cores)
    data["memory"]["total_bytes"] = _memory_bytes()

    vulkan_summary = command_output(["vulkaninfo", "--summary"])
    vulkan = vulkan_devices(vulkan_summary)
    nvidia = _nvidia_gpus()
    pci = _pci_accelerators()
    accelerators = nvidia + [device for device in pci if device["vendor"] != "NVIDIA"]
    data["accelerators"] = _enrich_accelerators_with_vulkan(accelerators or pci, vulkan)
    data["software"].update(
        {
            "cmake": command_output(["cmake", "--version"]),
            "compiler": command_output(["c++", "--version"]),
            "cuda_compiler": command_output(["nvcc", "--version"]),
            "vulkan": vulkan_summary,
        }
    )
    governor_path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    if governor_path.exists():
        data["power"]["cpu_governor"] = governor_path.read_text().strip()
    return data
