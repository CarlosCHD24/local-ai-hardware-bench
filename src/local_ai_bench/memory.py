from __future__ import annotations

import os
import platform
import re
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


MIB = 1024 * 1024


class MemorySampler:
    def __init__(self, process_group_id: int, config: dict[str, Any] | None = None) -> None:
        self.process_group_id = process_group_id
        self.config = config or {}
        self.interval = max(0.2, float(self.config.get("interval_ms", 1000)) / 1000)
        self.samples: list[dict[str, Any]] = []
        self.abort_reason: str | None = None
        self._started = time.monotonic()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._sample_once()
        self._thread = threading.Thread(target=self._run, name="memory-sampler", daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.interval + 2)
        self._sample_once(check_limits=False)
        return summarize_samples(self.samples, self.abort_reason, int(self.interval * 1000))

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            self._sample_once()

    def _sample_once(self, check_limits: bool = True) -> None:
        sample = memory_snapshot(self.process_group_id)
        sample["elapsed_seconds"] = round(time.monotonic() - self._started, 6)
        self.samples.append(sample)
        if not check_limits or self.abort_reason:
            return

        baseline = self.samples[0]
        swap_growth = max(0, int(sample.get("swap_used_bytes") or 0) - int(baseline.get("swap_used_bytes") or 0))
        max_swap = self.config.get("max_swap_growth_bytes")
        available = sample.get("available_percent")
        min_available = self.config.get("min_available_percent")
        if isinstance(max_swap, int) and max_swap > 0 and swap_growth > max_swap:
            self._abort(f"swap_growth_exceeded:{swap_growth}")
        elif (
            isinstance(min_available, (int, float))
            and isinstance(available, (int, float))
            and available < min_available
        ):
            self._abort(f"available_memory_below_limit:{available}")

    def _abort(self, reason: str) -> None:
        self.abort_reason = reason
        try:
            os.killpg(self.process_group_id, signal.SIGKILL)
        except ProcessLookupError:
            pass


def memory_snapshot(process_group_id: int | None = None) -> dict[str, Any]:
    system = platform.system()
    if system == "Darwin":
        return _macos_snapshot()
    if system == "Linux":
        return _linux_snapshot(process_group_id)
    return {"platform": system}


def summarize_samples(
    samples: list[dict[str, Any]], abort_reason: str | None, interval_ms: int
) -> dict[str, Any]:
    if not samples:
        return {"sample_count": 0, "sample_interval_ms": interval_ms, "abort_reason": abort_reason}
    first = samples[0]
    last = samples[-1]

    def maximum(key: str) -> int | float | None:
        values = [sample[key] for sample in samples if isinstance(sample.get(key), (int, float))]
        return max(values) if values else None

    def minimum(key: str) -> int | float | None:
        values = [sample[key] for sample in samples if isinstance(sample.get(key), (int, float))]
        return min(values) if values else None

    def delta(key: str) -> int | float | None:
        before = first.get(key)
        after = last.get(key)
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            return max(0, after - before)
        return None

    swap_before = first.get("swap_used_bytes")
    swap_peak = maximum("swap_used_bytes")
    compressed_before = first.get("compressed_bytes")
    compressed_peak = maximum("compressed_bytes")
    return {
        "sample_count": len(samples),
        "sample_interval_ms": interval_ms,
        "available_percent_min": minimum("available_percent"),
        "available_memory_before_bytes": first.get("available_memory_bytes"),
        "available_memory_min_bytes": minimum("available_memory_bytes"),
        "available_memory_drop_bytes": _positive_difference(
            first.get("available_memory_bytes"), minimum("available_memory_bytes")
        ),
        "swap_used_before_bytes": swap_before,
        "swap_used_peak_bytes": swap_peak,
        "swap_growth_bytes": _positive_difference(swap_peak, swap_before),
        "compressed_before_bytes": compressed_before,
        "compressed_peak_bytes": compressed_peak,
        "compressed_growth_bytes": _positive_difference(compressed_peak, compressed_before),
        "pageins_delta": delta("pageins"),
        "pageouts_delta": delta("pageouts"),
        "swapins_delta": delta("swapins"),
        "swapouts_delta": delta("swapouts"),
        "major_page_faults_delta": delta("major_page_faults"),
        "peak_device_memory_used_bytes": maximum("device_memory_used_bytes"),
        "device_memory_total_bytes": maximum("device_memory_total_bytes"),
        "peak_process_rss_bytes": maximum("process_rss_bytes"),
        "peak_process_swap_bytes": maximum("process_swap_bytes"),
        "peak_process_device_memory_used_bytes": maximum("process_device_memory_used_bytes"),
        "peak_process_group_size": maximum("process_group_size"),
        "abort_reason": abort_reason,
    }


def classify_pressure(memory: dict[str, Any], status: str) -> str:
    if status == "oom":
        return "oom"
    if status == "aborted_pressure" or memory.get("abort_reason"):
        return "aborted"
    if int(memory.get("swap_growth_bytes") or 0) >= 64 * MIB or int(memory.get("swapouts_delta") or 0) > 0:
        return "swapping"
    if int(memory.get("swap_used_before_bytes") or 0) >= 64 * MIB:
        return "swap_resident"
    if int(memory.get("compressed_growth_bytes") or 0) >= 256 * MIB:
        return "compressed"
    return "normal"


def _macos_snapshot() -> dict[str, Any]:
    vm_output = _command(["vm_stat"])
    swap_output = _command(["sysctl", "-n", "vm.swapusage"])
    pressure_output = _command(["memory_pressure", "-Q"])
    page_size_match = re.search(r"page size of (\d+) bytes", vm_output)
    page_size = int(page_size_match.group(1)) if page_size_match else 4096
    counters: dict[str, int] = {}
    for label, value in re.findall(r'^([^:]+):\s+(\d+)\.?$', vm_output, re.MULTILINE):
        counters[label.strip().lower()] = int(value)
    swap_match = re.search(r"used\s*=\s*([\d.]+)([KMG])", swap_output)
    free_match = re.search(r"memory free percentage:\s*(\d+)%", pressure_output, re.IGNORECASE)
    return {
        "platform": "Darwin",
        "available_percent": int(free_match.group(1)) if free_match else None,
        "swap_used_bytes": _scaled_bytes(swap_match.group(1), swap_match.group(2)) if swap_match else None,
        "compressed_bytes": counters.get("pages occupied by compressor", 0) * page_size,
        "pageins": counters.get("pageins"),
        "pageouts": counters.get("pageouts"),
        "swapins": counters.get("swapins"),
        "swapouts": counters.get("swapouts"),
    }


def _linux_snapshot(process_group_id: int | None = None) -> dict[str, Any]:
    meminfo = _read_key_values(Path("/proc/meminfo"))
    vmstat = _read_key_values(Path("/proc/vmstat"))
    total_kib = meminfo.get("MemTotal")
    available_kib = meminfo.get("MemAvailable")
    swap_total_kib = meminfo.get("SwapTotal")
    swap_free_kib = meminfo.get("SwapFree")
    process_ids = _linux_process_group_pids(process_group_id) if process_group_id is not None else set()
    process_rss, process_swap = _linux_process_memory(process_ids)
    device_used, device_total = _nvidia_memory()
    process_device_used = _nvidia_process_memory(process_ids)
    return {
        "platform": "Linux",
        "available_percent": (
            round(available_kib * 100 / total_kib, 2) if total_kib and available_kib is not None else None
        ),
        "available_memory_bytes": available_kib * 1024 if available_kib is not None else None,
        "swap_used_bytes": (
            max(0, swap_total_kib - swap_free_kib) * 1024
            if swap_total_kib is not None and swap_free_kib is not None
            else None
        ),
        "compressed_bytes": None,
        "pageins": vmstat.get("pgpgin"),
        "pageouts": vmstat.get("pgpgout"),
        "swapins": vmstat.get("pswpin"),
        "swapouts": vmstat.get("pswpout"),
        "major_page_faults": vmstat.get("pgmajfault"),
        "device_memory_used_bytes": device_used,
        "device_memory_total_bytes": device_total,
        "process_rss_bytes": process_rss,
        "process_swap_bytes": process_swap,
        "process_device_memory_used_bytes": process_device_used,
        "process_group_size": len(process_ids),
    }


def _nvidia_memory() -> tuple[int | None, int | None]:
    output = _command(
        [
            "nvidia-smi",
            "--query-gpu=memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ]
    )
    used = 0
    total = 0
    found = False
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2:
            continue
        try:
            used += int(float(parts[0])) * MIB
            total += int(float(parts[1])) * MIB
            found = True
        except ValueError:
            continue
    return (used, total) if found else (None, None)


def _nvidia_process_memory(process_ids: set[int]) -> int | None:
    if not process_ids:
        return None
    output = _command(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,used_gpu_memory",
            "--format=csv,noheader,nounits",
        ]
    )
    total = 0
    found = False
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
            memory_mib = float(parts[1])
        except ValueError:
            continue
        if pid in process_ids:
            total += int(memory_mib * MIB)
            found = True
    return total if found else None


def _linux_process_group_pids(
    process_group_id: int | None, proc_root: Path = Path("/proc")
) -> set[int]:
    if process_group_id is None:
        return set()
    try:
        entries = proc_root.iterdir()
    except OSError:
        return set()
    process_ids: set[int] = set()
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text(encoding="utf-8", errors="replace")
            closing_parenthesis = stat.rfind(")")
            if closing_parenthesis < 0:
                continue
            fields = stat[closing_parenthesis + 2 :].split()
            if len(fields) < 3 or int(fields[2]) != process_group_id:
                continue
            process_ids.add(int(entry.name))
        except (OSError, ValueError):
            continue
    return process_ids


def _linux_process_memory(
    process_ids: set[int], proc_root: Path = Path("/proc")
) -> tuple[int | None, int | None]:
    if not process_ids:
        return None, None
    rss_kib = 0
    swap_kib = 0
    found = False
    for pid in process_ids:
        values = _read_key_values(proc_root / str(pid) / "status")
        if not values:
            continue
        rss_kib += values.get("VmRSS", 0)
        swap_kib += values.get("VmSwap", 0)
        found = True
    return (rss_kib * 1024, swap_kib * 1024) if found else (None, None)


def _read_key_values(path: Path) -> dict[str, int]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    values: dict[str, int] = {}
    for line in lines:
        parts = line.replace(":", "").split()
        if len(parts) >= 2:
            try:
                values[parts[0]] = int(parts[1])
            except ValueError:
                pass
    return values


def _command(command: list[str]) -> str:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout


def _scaled_bytes(value: str, unit: str) -> int:
    scale = {"K": 1024, "M": MIB, "G": 1024 * MIB}[unit]
    return int(float(value) * scale)


def _positive_difference(after: Any, before: Any) -> int | float | None:
    if isinstance(after, (int, float)) and isinstance(before, (int, float)):
        return max(0, after - before)
    return None
