from __future__ import annotations

import platform
import shutil
from pathlib import Path
from typing import Any

from ..errors import BenchError
from . import linux, macos
from .common import executable_version


def collect_system(system_id: str, runtime_binary: Path | None = None) -> dict[str, Any]:
    system = platform.system()
    if system == "Linux":
        data = linux.collect(system_id)
    elif system == "Darwin":
        data = macos.collect(system_id)
    else:
        raise BenchError(f"Sistema no compatible en v1: {system}")
    if runtime_binary:
        data["software"]["llama_bench"] = executable_version(runtime_binary)
        data["software"]["llama_bench_path"] = runtime_binary.name
    return data


def detect_backend(requested: str = "auto") -> str:
    allowed = {"auto", "cpu", "cuda", "metal", "vulkan"}
    if requested not in allowed:
        raise BenchError(f"Backend no válido: {requested}")
    if requested != "auto":
        return requested
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return "metal"
    if platform.system() == "Linux" and shutil.which("nvcc") and shutil.which("nvidia-smi"):
        return "cuda"
    return "cpu"


def doctor_checks(backend: str = "auto", runtime_binary: Path | None = None) -> list[dict[str, Any]]:
    selected = detect_backend(backend)
    runtime_ready = runtime_binary is not None and runtime_binary.is_file()
    checks: list[dict[str, Any]] = [
        {"name": "platform", "ok": platform.system() in {"Linux", "Darwin"}, "value": platform.platform()},
    ]
    if runtime_binary is not None:
        checks.append({"name": "llama-bench", "ok": runtime_ready, "value": str(runtime_binary)})
    if not runtime_ready:
        checks.extend(
            [
                {"name": "git", "ok": shutil.which("git") is not None, "value": shutil.which("git")},
                {"name": "cmake", "ok": shutil.which("cmake") is not None, "value": shutil.which("cmake")},
                {"name": "compiler", "ok": shutil.which("c++") is not None or shutil.which("clang") is not None, "value": shutil.which("c++") or shutil.which("clang")},
            ]
        )
        if selected == "cuda":
            checks.extend(
                [
                    {"name": "nvcc", "ok": shutil.which("nvcc") is not None, "value": shutil.which("nvcc")},
                    {
                        "name": "nvidia-smi",
                        "ok": shutil.which("nvidia-smi") is not None,
                        "value": shutil.which("nvidia-smi"),
                    },
                ]
            )
        if selected == "metal":
            checks.append({"name": "xcode", "ok": shutil.which("xcode-select") is not None, "value": shutil.which("xcode-select")})
        if selected == "vulkan":
            checks.append(
                {"name": "glslc", "ok": shutil.which("glslc") is not None, "value": shutil.which("glslc")}
            )
    if selected == "vulkan":
        vulkaninfo = shutil.which("vulkaninfo")
        devices = linux.vulkan_devices() if vulkaninfo else []
        hardware_devices = [device for device in devices if not device["software"]]
        if hardware_devices:
            hardware_value = ", ".join(
                f"{device['name']} ({device['driver'] or 'driver desconocido'}, "
                f"{device['memory_architecture']})"
                for device in hardware_devices
            )
        elif devices:
            hardware_value = "sólo dispositivos Vulkan software: " + ", ".join(
                device["name"] for device in devices
            )
        else:
            hardware_value = "no detectado"
        checks.extend(
            [
                {"name": "vulkaninfo", "ok": vulkaninfo is not None, "value": vulkaninfo},
                {
                    "name": "vulkan_hardware_device",
                    "ok": bool(hardware_devices),
                    "value": hardware_value,
                },
            ]
        )
    checks.append({"name": "selected_backend", "ok": True, "value": selected})
    return checks
