from __future__ import annotations

import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def command_output(command: list[str], timeout: float = 5.0) -> str | None:
    if not command or shutil.which(command[0]) is None:
        return None
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and value else None


def base_system(system_id: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "system_id": system_id,
        "collected_at": utc_now(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine(),
        },
        "cpu": {
            "model": platform.processor() or "unknown",
            "logical_cores": os.cpu_count(),
        },
        "memory": {},
        "accelerators": [],
        "software": {
            "python": platform.python_version(),
        },
        "power": {},
    }


def executable_version(binary: Path) -> str | None:
    try:
        completed = subprocess.run(
            [str(binary), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = (completed.stdout + "\n" + completed.stderr).strip()
    return output.splitlines()[0] if output else None

