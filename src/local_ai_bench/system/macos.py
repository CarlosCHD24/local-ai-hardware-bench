from __future__ import annotations

import json
from typing import Any

from .common import base_system, command_output


def _sysctl(key: str) -> str | None:
    return command_output(["sysctl", "-n", key])


def _accelerators() -> list[dict[str, Any]]:
    output = command_output(["system_profiler", "SPDisplaysDataType", "-json"], timeout=20)
    if not output:
        return []
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []
    devices = []
    for item in data.get("SPDisplaysDataType", []):
        devices.append(
            {
                "kind": "gpu",
                "vendor": item.get("spdisplays_vendor", "Apple"),
                "name": item.get("sppci_model", item.get("_name", "Apple GPU")),
                "cores": item.get("sppci_cores"),
                "metal_support": item.get("spdisplays_metal"),
            }
        )
    return devices


def collect(system_id: str) -> dict[str, Any]:
    data = base_system(system_id)
    product = _sysctl("hw.model")
    data["platform"].update(
        {
            "distribution": "macOS",
            "product_model": product,
            "os_version": command_output(["sw_vers", "-productVersion"]),
            "build_version": command_output(["sw_vers", "-buildVersion"]),
        }
    )
    data["cpu"].update(
        {
            "model": _sysctl("machdep.cpu.brand_string") or product or "Apple Silicon",
            "physical_cores": _as_int(_sysctl("hw.physicalcpu")),
            "logical_cores": _as_int(_sysctl("hw.logicalcpu")),
        }
    )
    data["memory"]["total_bytes"] = _as_int(_sysctl("hw.memsize"))
    data["memory"]["unified"] = True
    data["accelerators"] = _accelerators()
    data["software"].update(
        {
            "cmake": command_output(["cmake", "--version"]),
            "compiler": command_output(["clang", "--version"]),
            "xcode": command_output(["xcode-select", "-p"]),
            "metal": True,
        }
    )
    return data


def _as_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None
