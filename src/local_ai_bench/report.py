from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from .errors import ResultValidationError
from .validate import validate_result_dir


def write_report(run_dir: Path) -> tuple[Path, Path]:
    data = validate_result_dir(run_dir)
    markdown = render_report(data)
    csv_text = render_csv(data["results"])
    report_path = run_dir / "report.md"
    csv_path = run_dir / "results.csv"
    report_path.write_text(markdown, encoding="utf-8")
    csv_path.write_text(csv_text, encoding="utf-8")
    return report_path, csv_path


def render_report(data: dict[str, Any]) -> str:
    system = data["system"]
    results = data["results"]
    records = results["results"]
    has_memory = any(record.get("memory") for record in records)
    lines = [
        f"# Benchmark: {results['system_id']}",
        "",
        f"- Suite: `{results['suite']['id']}`",
        f"- Ejecución: `{results['run_id']}`",
        f"- Backend configurado: `{results['runtime'].get('backend', 'unknown')}`",
        f"- CPU: {system.get('cpu', {}).get('model', 'unknown')}",
        f"- Memoria: {_format_bytes(system.get('memory', {}).get('total_bytes'))}",
        f"- Inicio: {results['started_at']}",
        f"- Fin: {results['finished_at']}",
        "",
    ]
    if has_memory:
        lines.extend(
            [
                "| Modelo | Perfil | Escenario | Estado | tokens/s | Pico RSS | RAM proceso | Swap proceso | VRAM proceso | RAM disponible Δ | Swap base | Swap pico | Swap Δ | Compresión Δ | Colocación | Presión | CUDA UM | Capas GPU |",
                "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---:|",
            ]
        )
    else:
        lines.extend(
            [
                "| Modelo | Escenario | Estado | tokens/s | Desv. | Pico RSS | Backend | Hilos | Capas GPU |",
                "|---|---|---:|---:|---:|---:|---|---:|---:|",
            ]
        )
    for record in records:
        metrics = record.get("metrics", {})
        details = record.get("runtime_details", {})
        backend = details.get("backend") or results["runtime"].get("backend", "—")
        if has_memory:
            memory = record.get("memory", {})
            lines.append(
                "| {model} | {profile} | {scenario} | {status} | {mean} | {rss} | {process_rss} | {process_swap} | {process_vram} | {available_drop} | {swap_before} | {swap_peak} | {swap} | {compressed} | {placement} | {pressure} | {cuda_um} | {layers} |".format(
                    model=record["model_id"],
                    profile=record.get("profile_id", "default"),
                    scenario=record["scenario_id"],
                    status=record["status"],
                    mean=_format_number(metrics.get("tokens_per_second_mean")),
                    rss=_format_bytes(metrics.get("peak_resident_memory_bytes")),
                    process_rss=_format_bytes(memory.get("peak_process_rss_bytes")),
                    process_swap=_format_bytes(memory.get("peak_process_swap_bytes")),
                    process_vram=_format_bytes(memory.get("peak_process_device_memory_used_bytes")),
                    available_drop=_format_bytes(memory.get("available_memory_drop_bytes")),
                    swap_before=_format_bytes(memory.get("swap_used_before_bytes")),
                    swap_peak=_format_bytes(memory.get("swap_used_peak_bytes")),
                    swap=_format_bytes(memory.get("swap_growth_bytes")),
                    compressed=_format_bytes(memory.get("compressed_growth_bytes")),
                    placement=memory.get("placement", "—"),
                    pressure=memory.get("pressure", "—"),
                    cuda_um=_format_bool(memory.get("cuda_unified_memory_enabled")),
                    layers=details.get("offloaded_layers", details.get("n_gpu_layers", "—")),
                )
            )
        else:
            lines.append(
                "| {model} | {scenario} | {status} | {mean} | {stddev} | {rss} | {backend} | {threads} | {layers} |".format(
                    model=record["model_id"],
                    scenario=record["scenario_id"],
                    status=record["status"],
                    mean=_format_number(metrics.get("tokens_per_second_mean")),
                    stddev=_format_number(metrics.get("tokens_per_second_stddev")),
                    rss=_format_bytes(metrics.get("peak_resident_memory_bytes")),
                    backend=backend,
                    threads=details.get("n_threads", "—"),
                    layers=details.get("n_gpu_layers", "—"),
                )
            )

    failures = [record for record in results["results"] if record["status"] != "ok"]
    if failures:
        lines.extend(["", "## Incidencias", ""])
        for record in failures:
            error = (record.get("error") or "Sin detalle").replace("\n", " ")
            lines.append(
                f"- `{record['model_id']} / {record.get('profile_id', 'default')} / {record['scenario_id']}`: {error}"
            )
    lines.extend(
        [
            "",
            "> Los resultados describen el sistema completo (hardware, sistema operativo, drivers y runtime).",
            "",
        ]
    )
    return "\n".join(lines)


def render_csv(results: dict[str, Any]) -> str:
    output = io.StringIO()
    fields = [
        "system_id",
        "suite_id",
        "run_id",
        "model_id",
        "profile_id",
        "scenario_id",
        "status",
        "tokens_per_second_mean",
        "tokens_per_second_stddev",
        "peak_resident_memory_bytes",
        "placement",
        "pressure",
        "swap_growth_bytes",
        "compressed_growth_bytes",
        "peak_device_memory_used_bytes",
        "peak_process_rss_bytes",
        "peak_process_swap_bytes",
        "peak_process_device_memory_used_bytes",
        "available_memory_drop_bytes",
        "cuda_unified_memory_enabled",
        "backend",
        "n_threads",
        "n_gpu_layers",
        "error",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for record in results["results"]:
        metrics = record.get("metrics", {})
        details = record.get("runtime_details", {})
        memory = record.get("memory", {})
        backend = details.get("backend") or results["runtime"].get("backend")
        writer.writerow(
            {
                "system_id": results["system_id"],
                "suite_id": results["suite"]["id"],
                "run_id": results["run_id"],
                "model_id": record["model_id"],
                "profile_id": record.get("profile_id", "default"),
                "scenario_id": record["scenario_id"],
                "status": record["status"],
                "tokens_per_second_mean": metrics.get("tokens_per_second_mean"),
                "tokens_per_second_stddev": metrics.get("tokens_per_second_stddev"),
                "peak_resident_memory_bytes": metrics.get("peak_resident_memory_bytes"),
                "placement": memory.get("placement"),
                "pressure": memory.get("pressure"),
                "swap_growth_bytes": memory.get("swap_growth_bytes"),
                "compressed_growth_bytes": memory.get("compressed_growth_bytes"),
                "peak_device_memory_used_bytes": memory.get("peak_device_memory_used_bytes"),
                "peak_process_rss_bytes": memory.get("peak_process_rss_bytes"),
                "peak_process_swap_bytes": memory.get("peak_process_swap_bytes"),
                "peak_process_device_memory_used_bytes": memory.get(
                    "peak_process_device_memory_used_bytes"
                ),
                "available_memory_drop_bytes": memory.get("available_memory_drop_bytes"),
                "cuda_unified_memory_enabled": memory.get("cuda_unified_memory_enabled"),
                "backend": backend,
                "n_threads": details.get("n_threads"),
                "n_gpu_layers": details.get("n_gpu_layers"),
                "error": record.get("error"),
            }
        )
    return output.getvalue()


def compare_runs(run_dirs: list[Path]) -> str:
    if len(run_dirs) < 2:
        raise ResultValidationError("compare necesita al menos dos directorios de resultados")
    validated = [validate_result_dir(path) for path in run_dirs]
    datasets = [item["results"] for item in validated]
    suite_ids = {data["suite"]["id"] for data in datasets}
    if len(suite_ids) != 1:
        raise ResultValidationError("No se pueden comparar suites diferentes")
    model_sets = [_model_fingerprint(item["manifest"].get("models", [])) for item in validated]
    if any(fingerprint != model_sets[0] for fingerprint in model_sets[1:]):
        raise ResultValidationError("Los artefactos o revisiones de modelos no coinciden")

    systems = [data["system_id"] for data in datasets]
    keys: list[tuple[str, str, str]] = []
    for record in datasets[0]["results"]:
        keys.append((record["model_id"], record.get("profile_id", "default"), record["scenario_id"]))
    indexes = [
        {
            (record["model_id"], record.get("profile_id", "default"), record["scenario_id"]): record
            for record in data["results"]
        }
        for data in datasets
    ]
    lines = [
        f"# Comparación `{next(iter(suite_ids))}`",
        "",
        "| Modelo | Perfil | Escenario | " + " | ".join(systems) + " |",
        "|---|---|---|" + "---:|" * len(systems),
    ]
    for model_id, profile_id, scenario_id in keys:
        values = []
        for index in indexes:
            record = index.get((model_id, profile_id, scenario_id))
            if not record or record["status"] != "ok":
                values.append("—")
            else:
                values.append(_format_number(record["metrics"].get("tokens_per_second_mean")))
        lines.append(f"| {model_id} | {profile_id} | {scenario_id} | " + " | ".join(values) + " |")
    lines.extend(["", "Valores expresados en tokens/s.", ""])
    return "\n".join(lines)


def _format_number(value: Any) -> str:
    return f"{value:.2f}" if isinstance(value, (int, float)) else "—"


def _format_bytes(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "desconocida"
    return f"{value / (1024**3):.1f} GiB"


def _format_bool(value: Any) -> str:
    if value is True:
        return "sí"
    if value is False:
        return "no"
    return "—"


def _model_fingerprint(models: list[dict[str, Any]]) -> tuple[Any, ...]:
    return tuple(
        (
            model.get("id"),
            model.get("revision"),
            tuple(
                (artifact.get("filename"), artifact.get("sha256"))
                for artifact in model.get("artifacts", [])
            ),
        )
        for model in models
    )
