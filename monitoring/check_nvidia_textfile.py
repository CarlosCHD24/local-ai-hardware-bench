"""Validador de sólo lectura del textfile collector de NVIDIA.

Recorre los ``*.prom`` de un directorio (por defecto el del textfile collector
de node_exporter), los parsea como texto de exposición Prometheus y comprueba:

1. que exista al menos un ``.prom``;
2. que el más reciente no supere ``--max-age`` segundos;
3. que contenga ``local_ai_gpu_scrape_success 1``;
4. que estén las métricas GPU nucleares (utilización, memoria usada/total,
   temperatura y potencia).

Los nombres de fichero y de métricas se reutilizan de ``nvidia_textfile`` y
``nvidia_metrics`` para no duplicar constantes. Sólo usa la stdlib.

Uso::

    python3 monitoring/check_nvidia_textfile.py \
        --directory /var/lib/node_exporter/textfile_collector --max-age 45
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):  # ejecución directa `python monitoring/check_nvidia_textfile.py`
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from monitoring import nvidia_metrics, nvidia_textfile

DEFAULT_MAX_AGE = 45

#: Métrica de éxito del scrape, derivada de la definición del colector.
SUCCESS_METRIC = next(
    name for name, _, _ in nvidia_metrics.METRICS if name.endswith("scrape_success")
)
#: Métricas GPU nucleares, derivadas de la definición del colector.
GPU_METRICS = tuple(
    name
    for name, _, _ in nvidia_metrics.METRICS
    if name.endswith(
        (
            "utilization_ratio",
            "memory_used_bytes",
            "memory_total_bytes",
            "temperature_celsius",
            "power_watts",
        )
    )
)


@dataclass(frozen=True)
class TextfileResult:
    """Resultado individual de una comprobación del textfile."""

    name: str
    ok: bool
    message: str
    required: bool = True

    @property
    def status(self) -> str:
        return "ok" if self.ok else "error"

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "required": self.required,
            "message": self.message,
        }


def parse_prometheus(text: str) -> dict[str, list[float]]:
    """Extrae ``nombre_base -> [valores]`` del texto de exposición Prometheus."""
    metrics: dict[str, list[float]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 2:
            continue
        name = fields[0].split("{", 1)[0].strip()
        if not name:
            continue
        try:
            value = float(fields[1])
        except ValueError:
            continue
        metrics.setdefault(name, []).append(value)
    return metrics


def _present(directory: Path, files: list[Path]) -> TextfileResult:
    ok = bool(files)
    if ok:
        message = f"textfile: {len(files)} fichero(s) .prom en {directory}"
    else:
        message = f"textfile: sin ficheros .prom en {directory}"
    return TextfileResult("textfile-present", ok, message)


def evaluate(
    directory: str | Path,
    max_age: float = DEFAULT_MAX_AGE,
    now: float | None = None,
) -> list[TextfileResult]:
    """Ejecuta las comprobaciones sobre ``directory``."""
    directory = Path(directory)
    files = sorted(directory.glob("*.prom")) if directory.is_dir() else []
    results = [_present(directory, files)]
    if not files:
        return results

    if now is None:
        now = time.time()
    newest = max(files, key=lambda path: path.stat().st_mtime)
    age = now - newest.stat().st_mtime
    results.append(
        TextfileResult(
            "textfile-fresh",
            age <= max_age,
            (
                f"frescura: {newest.name} tiene {age:.1f}s "
                f"(<= {max_age:g}s)"
                if age <= max_age
                else f"frescura: {newest.name} tiene {age:.1f}s (> {max_age:g}s)"
            ),
        )
    )

    metrics = parse_prometheus(newest.read_text(encoding="utf-8"))
    success_values = metrics.get(SUCCESS_METRIC, [])
    success = any(value == 1 for value in success_values)
    if success:
        success_message = f"scrape_success: {newest.name} expone {SUCCESS_METRIC} 1"
    elif success_values:
        success_message = (
            f"scrape_success: {newest.name} expone {SUCCESS_METRIC} "
            f"{success_values[0]:g} (se espera 1)"
        )
    else:
        success_message = (
            f"scrape_success: {newest.name} no expone {SUCCESS_METRIC}"
        )
    results.append(TextfileResult("textfile-scrape-success", success, success_message))

    missing = [name for name in GPU_METRICS if name not in metrics]
    gpu_ok = not missing
    if gpu_ok:
        gpu_message = f"metricas GPU: {len(GPU_METRICS)}/{len(GPU_METRICS)} presentes"
    else:
        gpu_message = (
            f"metricas GPU: faltan {', '.join(missing)} "
            f"({len(GPU_METRICS) - len(missing)}/{len(GPU_METRICS)} presentes)"
        )
    results.append(TextfileResult("textfile-gpu-metrics", gpu_ok, gpu_message))

    return results


def exit_code(results: list[TextfileResult]) -> int:
    return 1 if any(not result.ok for result in results) else 0


def render_text(results: list[TextfileResult], code: int) -> str:
    lines = [f"[{result.status.upper()}] {result.message}" for result in results]
    lines.append(f"checks={len(results)} exit={code}")
    return "\n".join(lines)


def render_json(results: list[TextfileResult], code: int) -> str:
    return json.dumps(
        {
            "ok": code == 0,
            "exit_code": code,
            "checks": [result.as_dict() for result in results],
        },
        indent=2,
        sort_keys=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--directory",
        required=True,
        help="directorio del textfile collector a inspeccionar",
    )
    parser.add_argument(
        "--max-age",
        type=float,
        default=DEFAULT_MAX_AGE,
        help="antigüedad máxima en segundos (por defecto: %(default)s)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="emite el informe como JSON en stdout",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_age <= 0:
        print("max-age debe ser positivo", file=sys.stderr)
        return 2
    results = evaluate(args.directory, max_age=args.max_age)
    code = exit_code(results)
    if args.as_json:
        print(render_json(results, code))
    else:
        print(render_text(results, code))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
