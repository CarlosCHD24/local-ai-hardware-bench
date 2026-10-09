"""Colector de una muestra NVIDIA en formato de exposición Prometheus."""

from __future__ import annotations

import argparse
import csv
import math
import subprocess
import sys


QUERY = [
    "nvidia-smi",
    "--query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit",
    "--format=csv,noheader,nounits",
]
METRICS = (
    ("local_ai_gpu_utilization_ratio", "Utilización instantánea de la GPU.", "gauge"),
    ("local_ai_gpu_memory_used_bytes", "Memoria de GPU utilizada en bytes.", "gauge"),
    ("local_ai_gpu_memory_total_bytes", "Memoria total de GPU en bytes.", "gauge"),
    ("local_ai_gpu_temperature_celsius", "Temperatura de la GPU en grados Celsius.", "gauge"),
    ("local_ai_gpu_power_watts", "Potencia instantánea de la GPU en vatios.", "gauge"),
    ("local_ai_gpu_power_limit_watts", "Límite de potencia de la GPU en vatios.", "gauge"),
    ("local_ai_gpu_scrape_success", "Éxito de la última recopilación NVIDIA.", "gauge"),
)


def _number(value: str) -> float:
    parsed = float(value.strip())
    if not math.isfinite(parsed):
        raise ValueError("número no finito")
    return parsed


def _format(value: float) -> str:
    return format(value, ".15g")


def _parse_rows(output: str) -> list[tuple[int, tuple[float, ...]]]:
    rows: list[tuple[int, tuple[float, ...]]] = []
    for row in csv.reader(output.splitlines()):
        if len(row) != 7:
            raise ValueError("fila NVIDIA incompleta")
        index_text = row[0].strip()
        if not index_text.isdecimal():
            raise ValueError("índice de GPU inválido")
        values = tuple(_number(value) for value in row[1:])
        rows.append((int(index_text), values))
    if not rows or len({index for index, _ in rows}) != len(rows):
        raise ValueError("sin GPUs o índices duplicados")
    return sorted(rows)


def _render(rows: list[tuple[int, tuple[float, ...]]]) -> str:
    lines = [f"# HELP {name} {help_text}\n# TYPE {name} {kind}" for name, help_text, kind in METRICS]
    for index, values in rows:
        utilization, memory_used, memory_total, temperature, power, power_limit = values
        label = f'{{gpu="{index}"}}'
        lines.extend(
            (
                f"local_ai_gpu_utilization_ratio{label} {_format(utilization / 100)}",
                f"local_ai_gpu_memory_used_bytes{label} {_format(memory_used * 1024 * 1024)}",
                f"local_ai_gpu_memory_total_bytes{label} {_format(memory_total * 1024 * 1024)}",
                f"local_ai_gpu_temperature_celsius{label} {_format(temperature)}",
                f"local_ai_gpu_power_watts{label} {_format(power)}",
                f"local_ai_gpu_power_limit_watts{label} {_format(power_limit)}",
                f"local_ai_gpu_scrape_success{label} 1",
            )
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Ejecuta una única recopilación y escribe métricas sin datos externos."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=5)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        print("timeout debe ser positivo", file=sys.stderr)
        return 2
    try:
        result = subprocess.run(QUERY, capture_output=True, text=True, timeout=args.timeout)
        if result.returncode != 0:
            raise RuntimeError("nvidia-smi falló")
        print(_render(_parse_rows(result.stdout)), end="")
        return 0
    except (FileNotFoundError, subprocess.TimeoutExpired, RuntimeError, ValueError, csv.Error):
        print("local_ai_gpu_scrape_success 0")
        print("nvidia-smi scrape failed", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
