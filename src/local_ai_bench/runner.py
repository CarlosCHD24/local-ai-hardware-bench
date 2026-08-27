from __future__ import annotations

import json
import os
import platform
import re
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import LoadedConfig, selected_profiles
from .errors import BenchError
from .memory import MemorySampler, classify_pressure
from .models import model_primary_path, verify_model
from .runtimes.llamacpp import LlamaCppRuntime
from .system import collect_system


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_id_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def execute_suite(
    config: LoadedConfig,
    runtime: LlamaCppRuntime,
    home: Path,
    output_root: Path,
    system_id: str,
    models: list[dict[str, Any]],
    threads: int | None = None,
    force_hash: bool = False,
    fail_fast: bool = False,
    profiles: list[dict[str, Any]] | None = None,
) -> Path:
    binary = runtime.binary
    if not binary.is_file():
        raise BenchError(f"No existe {binary}; ejecuta prepare o utiliza --runtime-binary")
    for model in models:
        verify_model(home, model, force_hash=force_hash)
    profiles = profiles or selected_profiles(config.suite, backend=runtime.backend)

    run_id = run_id_now()
    run_dir = output_root / config.suite["id"] / system_id / run_id
    suffix = 1
    while run_dir.exists():
        run_dir = output_root / config.suite["id"] / system_id / f"{run_id}-{suffix}"
        suffix += 1
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True)

    system = collect_system(system_id, binary)
    system["software"]["configured_backend"] = runtime.backend
    system["software"]["llama_cpp_revision"] = config.suite["runtime"]["revision"]
    write_json(run_dir / "system.json", system)

    model_snapshot = [_model_snapshot(model) for model in models]
    manifest = {
        "schema_version": 1,
        "suite": config.suite,
        "model_manifest_id": config.manifest["id"],
        "models": model_snapshot,
    }
    write_json(run_dir / "manifest.json", manifest)

    result: dict[str, Any] = {
        "schema_version": 1,
        "suite": {"id": config.suite["id"], "schema_version": config.suite["schema_version"]},
        "system_id": system_id,
        "run_id": run_dir.name,
        "started_at": iso_now(),
        "finished_at": iso_now(),
        "runtime": {
            "id": config.suite["runtime"]["id"],
            "revision": config.suite["runtime"]["revision"],
            "backend": runtime.backend,
            "binary_version": system["software"].get("llama_bench"),
            "threads_override": threads,
        },
        "models": model_snapshot,
        "results": [],
    }
    write_json(run_dir / "results.json", result)

    timeout = int(config.suite.get("timeout_seconds", 300))
    monitoring = config.suite.get("memory_monitoring")
    cooldown = float(config.suite.get("cooldown_seconds", 0))
    skip_after_memory_failure = bool(config.suite.get("skip_remaining_after_memory_failure", False))
    skip_after_capacity_failure = bool(config.suite.get("skip_remaining_after_capacity_failure", False))
    model_time_budget = config.suite.get("model_time_budget_seconds")
    blocked_profiles: set[tuple[str, str]] = set()
    blocked_models: dict[str, str] = {}
    for model in models:
        model_deadline = (
            time.monotonic() + float(model_time_budget)
            if isinstance(model_time_budget, (int, float)) and model_time_budget > 0
            else None
        )
        for profile in profiles:
            profile_id = profile["id"]
            profile_key = (model["id"], profile_id)
            for scenario in config.suite["scenarios"]:
                label = f"{model['id']} / {profile_id} / {scenario['id']}"
                prefix = f"{model['id']}--{profile_id}--{scenario['id']}"
                raw_file = raw_dir / f"{prefix}.json"
                stderr_file = raw_dir / f"{prefix}.stderr.txt"
                command_file = raw_dir / f"{prefix}.command.json"
                memory_file = raw_dir / f"{prefix}.memory.json"
                if model_deadline is not None and time.monotonic() >= model_deadline:
                    blocked_models.setdefault(model["id"], "Omitida tras agotar el presupuesto temporal del modelo")
                if model["id"] in blocked_models or profile_key in blocked_profiles:
                    print(f"↷ {label}: skipped")
                    raw_file.write_text("", encoding="utf-8")
                    reason = blocked_models.get(model["id"], "Omitida tras fallo de memoria")
                    record = _failure_record(model, scenario, raw_file, reason, "skipped")
                    record["profile_id"] = profile_id
                    result["results"].append(record)
                    result["finished_at"] = iso_now()
                    write_json(run_dir / "results.json", result)
                    continue

                scenario_timeout = _remaining_timeout(timeout, model_deadline)

                print(f"▶ {label}")
                command = runtime.command(
                    model_primary_path(home, model),
                    scenario,
                    config.suite["repetitions"],
                    threads,
                    profile,
                )
                write_json(
                    command_file,
                    {
                        "command": _portable_command(command, home),
                        "environment": _portable_environment(runtime, profile),
                    },
                )

                try:
                    _warmup(
                        runtime,
                        model_primary_path(home, model),
                        scenario,
                        config.suite["warmup_runs"],
                        threads,
                        scenario_timeout,
                        profile,
                        monitoring,
                    )
                    scenario_timeout = _remaining_timeout(timeout, model_deadline)
                    measured_command = _with_memory_measurement(command)
                    completed, memory_summary, memory_samples = _run_monitored_command(
                        measured_command,
                        scenario_timeout,
                        runtime.environment(profile),
                        monitoring,
                    )
                    raw_file.write_text(completed.stdout, encoding="utf-8")
                    stderr_file.write_text(completed.stderr, encoding="utf-8")
                    parsed: list[dict[str, Any]] | None = None
                    parse_error: ValueError | None = None
                    try:
                        parsed = runtime.parse(completed.stdout)
                    except ValueError as exc:
                        parse_error = exc
                    if completed.returncode != 0 and parsed is None:
                        status = _failure_status(completed.returncode, completed.stderr, memory_summary)
                        record = _failure_record(model, scenario, raw_file, completed.stderr, status)
                    elif parsed is None:
                        raise parse_error or ValueError("Salida no válida de llama-bench")
                    else:
                        record = _success_record(
                            model,
                            scenario,
                            raw_file,
                            parsed,
                            _peak_resident_memory_bytes(completed.stderr),
                            completed.stderr,
                        )
                    if monitoring:
                        memory_summary["samples_file"] = str(memory_file.relative_to(run_dir))
                        _finish_memory_record(memory_summary, record, runtime.backend, model, profile)
                        record["memory"] = memory_summary
                        write_json(memory_file, {"summary": memory_summary, "samples": memory_samples})
                except subprocess.TimeoutExpired as exc:
                    stdout = _text(exc.stdout)
                    stderr = _text(exc.stderr)
                    raw_file.write_text(stdout, encoding="utf-8")
                    stderr_file.write_text(stderr, encoding="utf-8")
                    record = _failure_record(
                        model,
                        scenario,
                        raw_file,
                        f"Timeout tras {scenario_timeout:.1f}s",
                        "timeout",
                    )
                    memory_summary = getattr(exc, "memory_summary", {})
                    memory_samples = getattr(exc, "memory_samples", [])
                    if monitoring and memory_summary:
                        memory_summary["samples_file"] = str(memory_file.relative_to(run_dir))
                        _finish_memory_record(memory_summary, record, runtime.backend, model, profile)
                        record["memory"] = memory_summary
                        write_json(memory_file, {"summary": memory_summary, "samples": memory_samples})
                except (OSError, ValueError) as exc:
                    record = _failure_record(model, scenario, raw_file, str(exc), "failed")

                record["profile_id"] = profile_id
                record["raw_file"] = str(raw_file.relative_to(run_dir))
                result["results"].append(record)
                result["finished_at"] = iso_now()
                write_json(run_dir / "results.json", result)
                status_mark = "✓" if record["status"] == "ok" else "✗"
                print(f"{status_mark} {label}: {_record_summary(record)}")
                if skip_after_memory_failure and record["status"] in {"oom", "aborted_pressure"}:
                    blocked_profiles.add(profile_key)
                if skip_after_capacity_failure and record["status"] in {
                    "timeout",
                    "oom",
                    "aborted_pressure",
                }:
                    blocked_models[model["id"]] = "Omitida tras alcanzar el límite de capacidad"
                if model_deadline is not None and time.monotonic() >= model_deadline:
                    blocked_models[model["id"]] = "Omitida tras agotar el presupuesto temporal del modelo"
                if fail_fast and record["status"] != "ok":
                    from .report import write_report

                    write_report(run_dir)
                    raise BenchError(f"La prueba falló: {label}")
                if cooldown and model["id"] not in blocked_models:
                    cooldown_remaining = cooldown
                    if model_deadline is not None:
                        cooldown_remaining = min(
                            cooldown, max(0.0, model_deadline - time.monotonic())
                        )
                    if cooldown_remaining:
                        time.sleep(cooldown_remaining)

    from .report import write_report

    write_report(run_dir)
    return run_dir


def _warmup(
    runtime: LlamaCppRuntime,
    model_path: Path,
    scenario: dict[str, Any],
    repetitions: int,
    threads: int | None,
    timeout: float,
    profile: dict[str, Any] | None = None,
    monitoring: dict[str, Any] | None = None,
) -> None:
    if repetitions < 1:
        return
    command = runtime.command(model_path, scenario, repetitions, threads, profile)
    if monitoring:
        completed, _, _ = _run_monitored_command(
            command, timeout, runtime.environment(profile), monitoring
        )
    else:
        completed = _run_command(command, timeout, runtime.environment(profile))
    if completed.returncode != 0:
        raise OSError(f"El calentamiento falló: {completed.stderr.strip()[-500:]}")


def _success_record(
    model: dict[str, Any],
    scenario: dict[str, Any],
    raw_file: Path,
    parsed: list[dict[str, Any]],
    peak_resident_memory_bytes: int | None = None,
    stderr: str = "",
) -> dict[str, Any]:
    runtime_record = parsed[0]
    samples_ts = runtime_record.get("samples_ts") or []
    samples_ns = runtime_record.get("samples_ns") or []
    runtime_backend = runtime_record.get("backend") or runtime_record.get("backends")
    runtime_details = {
        key: runtime_record.get(key)
        for key in (
            "model_type",
            "model_size",
            "model_n_params",
            "n_batch",
            "n_ubatch",
            "n_threads",
            "n_gpu_layers",
            "main_gpu",
            "tensor_split",
            "split_mode",
            "cpu_mask",
            "cpu_strict",
            "poll",
            "type_k",
            "type_v",
            "flash_attn",
            "devices",
            "fit_target",
            "fit_min_ctx",
            "load_mode",
            "use_mmap",
            "no_host",
            "test",
        )
        if key in runtime_record
    }
    if runtime_backend:
        # llama.cpp has emitted both `backend` and `backends` across revisions.
        runtime_details["backend"] = runtime_backend
    runtime_details.update(_parse_runtime_placement(stderr))
    return {
        "model_id": model["id"],
        "scenario_id": scenario["id"],
        "status": "ok",
        "metrics": {
            "tokens_per_second_mean": _number(runtime_record.get("avg_ts")),
            "tokens_per_second_stddev": _number(runtime_record.get("stddev_ts")),
            "duration_ns_mean": _number(runtime_record.get("avg_ns")),
            "duration_ns_stddev": _number(runtime_record.get("stddev_ns")),
            "samples_tokens_per_second": samples_ts,
            "samples_duration_ns": samples_ns,
            "sample_count": max(len(samples_ts), len(samples_ns)),
            "peak_resident_memory_bytes": peak_resident_memory_bytes,
        },
        "runtime_details": runtime_details,
        "raw_file": str(raw_file),
        "error": None,
    }


def _failure_record(
    model: dict[str, Any], scenario: dict[str, Any], raw_file: Path, error: str, status: str
) -> dict[str, Any]:
    return {
        "model_id": model["id"],
        "scenario_id": scenario["id"],
        "status": status,
        "metrics": {},
        "runtime_details": {},
        "raw_file": str(raw_file),
        "error": error.strip()[-2000:] or "Error sin mensaje",
    }


def _failure_status(returncode: int, stderr: str, memory: dict[str, Any]) -> str:
    if memory.get("abort_reason"):
        return "aborted_pressure"
    oom_pattern = r"out of memory|failed to allocate|cannot allocate memory|insufficient memory|cuda.*alloc.*failed"
    if returncode in {-9, 137} or re.search(oom_pattern, stderr, re.IGNORECASE):
        return "oom"
    return "failed"


def _finish_memory_record(
    memory: dict[str, Any],
    record: dict[str, Any],
    backend: str,
    model: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> None:
    details = record.get("runtime_details", {})
    for key in (
        "offloaded_layers",
        "total_layers",
        "host_model_bytes",
        "device_model_bytes",
        "host_kv_bytes",
        "device_kv_bytes",
        "host_compute_bytes",
        "device_compute_bytes",
    ):
        if details.get(key) is not None:
            memory[key] = details[key]
    gpu_layers = details.get("offloaded_layers", details.get("n_gpu_layers"))
    total_layers = details.get("total_layers") or model.get("layers")
    if not isinstance(gpu_layers, int) or gpu_layers <= 0:
        placement = "cpu" if record["status"] == "ok" else "unknown"
    elif isinstance(total_layers, int) and gpu_layers < total_layers:
        placement = "hybrid"
    elif backend == "metal":
        placement = "unified_gpu"
    else:
        placement = "gpu_full"
    memory["placement"] = placement
    memory["cuda_unified_memory_enabled"] = bool(
        backend == "cuda" and (profile or {}).get("cuda_unified_memory")
    )
    memory["pressure"] = classify_pressure(memory, record["status"])


def _parse_runtime_placement(stderr: str) -> dict[str, Any]:
    details: dict[str, Any] = {}
    offload_matches = re.findall(r"offloaded\s+(\d+)/(\d+)\s+layers to GPU", stderr)
    if offload_matches:
        details["offloaded_layers"] = int(offload_matches[-1][0])
        details["total_layers"] = int(offload_matches[-1][1])

    totals = {
        "host_model_bytes": 0,
        "device_model_bytes": 0,
        "host_kv_bytes": 0,
        "device_kv_bytes": 0,
        "host_compute_bytes": 0,
        "device_compute_bytes": 0,
    }
    found: set[str] = set()
    pattern = r":\s+(\S+)\s+(model|KV|compute) buffer size\s*=\s*([\d.]+)\s+MiB"
    for buffer_name, buffer_kind, size in re.findall(pattern, stderr, re.IGNORECASE):
        location = "device" if re.search(r"metal|mtl|cuda|vulkan|hip|sycl|gpu", buffer_name, re.I) else "host"
        key = f"{location}_{buffer_kind.lower()}_bytes"
        totals[key] += int(float(size) * 1024 * 1024)
        found.add(key)
    for key in found:
        details[key] = totals[key]
    return details


def _model_snapshot(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": model["id"],
        "parameters_billions": model.get("parameters_billions"),
        "layers": model.get("layers"),
        "repository": model["repository"],
        "revision": model["revision"],
        "primary_artifact": model["primary_artifact"],
        "artifacts": [
            {
                "filename": artifact["filename"],
                "size_bytes": artifact["size_bytes"],
                "sha256": artifact["sha256"],
            }
            for artifact in model["artifacts"]
        ],
    }


def _portable_command(command: list[str], home: Path) -> list[str]:
    home_text = str(home)
    return [part.replace(home_text, "${LOCAL_AI_BENCH_HOME}") for part in command]


def _portable_environment(runtime: LlamaCppRuntime, profile: dict[str, Any]) -> dict[str, str]:
    environment: dict[str, str] = {}
    if profile.get("cuda_unified_memory") and runtime.backend == "cuda":
        environment["GGML_CUDA_ENABLE_UNIFIED_MEMORY"] = "1"
    return environment


def _number(value: Any) -> float | int | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _record_summary(record: dict[str, Any]) -> str:
    if record["status"] != "ok":
        return record["status"]
    value = record["metrics"].get("tokens_per_second_mean")
    return f"{value:.2f} tokens/s" if isinstance(value, (int, float)) else "sin métrica"


def _text(value: bytes | str | None) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value or ""


def _with_memory_measurement(command: list[str]) -> list[str]:
    time_binary = Path("/usr/bin/time")
    if not time_binary.is_file():
        return command
    option = "-l" if platform.system() == "Darwin" else "-v"
    return [str(time_binary), option, *command]


def _peak_resident_memory_bytes(stderr: str) -> int | None:
    if platform.system() == "Darwin":
        match = re.search(r"^\s*(\d+)\s+maximum resident set size", stderr, re.MULTILINE)
        return int(match.group(1)) if match else None
    match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", stderr)
    return int(match.group(1)) * 1024 if match else None


def _run_command(
    command: list[str], timeout: float, environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env=environment,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            process.kill()
        stdout, stderr = process.communicate()
        raise subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr) from exc
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def _remaining_timeout(timeout: float, deadline: float | None) -> float:
    if deadline is None:
        return float(timeout)
    return min(float(timeout), max(0.0, deadline - time.monotonic()))


def _run_monitored_command(
    command: list[str],
    timeout: float,
    environment: dict[str, str] | None,
    monitoring: dict[str, Any] | None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any], list[dict[str, Any]]]:
    if not monitoring:
        return _run_command(command, timeout, environment), {}, []
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env=environment,
    )
    sampler = MemorySampler(process.pid, monitoring)
    sampler.start()
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as original:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            process.kill()
        stdout, stderr = process.communicate()
        memory_summary = sampler.stop()
        error = subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr)
        setattr(error, "memory_summary", memory_summary)
        setattr(error, "memory_samples", sampler.samples)
        raise error from original
    memory_summary = sampler.stop()
    return (
        subprocess.CompletedProcess(command, process.returncode, stdout, stderr),
        memory_summary,
        sampler.samples,
    )
