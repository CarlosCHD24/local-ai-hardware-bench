from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import read_json
from .errors import ResultValidationError


def validate_result_dir(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    required = ["manifest.json", "system.json", "results.json"]
    missing = [name for name in required if not (run_dir / name).is_file()]
    if missing:
        raise ResultValidationError(f"Faltan archivos en {run_dir}: {', '.join(missing)}")

    manifest = read_json(run_dir / "manifest.json")
    system = read_json(run_dir / "system.json")
    results = read_json(run_dir / "results.json")
    if results.get("schema_version") != 1:
        raise ResultValidationError("schema_version de resultados no compatible")
    if system.get("system_id") != results.get("system_id"):
        raise ResultValidationError("system_id no coincide entre system.json y results.json")
    suite_id = manifest.get("suite", {}).get("id")
    if results.get("suite", {}).get("id") != suite_id:
        raise ResultValidationError("La suite no coincide entre manifest.json y results.json")

    keys: set[tuple[str, str, str]] = set()
    known_models = {model.get("id") for model in results.get("models", [])}
    for record in results.get("results", []):
        key = (
            record.get("model_id"),
            record.get("profile_id", "default"),
            record.get("scenario_id"),
        )
        if key in keys:
            raise ResultValidationError(f"Resultado duplicado: {key[0]} / {key[1]} / {key[2]}")
        keys.add(key)
        if record.get("model_id") not in known_models:
            raise ResultValidationError(f"Resultado para modelo desconocido: {record.get('model_id')}")
        if record.get("status") not in {
            "ok",
            "failed",
            "timeout",
            "skipped",
            "oom",
            "aborted_pressure",
        }:
            raise ResultValidationError(f"Estado no válido en {key[0]} / {key[1]} / {key[2]}")
        raw_file = record.get("raw_file")
        if raw_file and not (run_dir / raw_file).is_file() and record.get("status") == "ok":
            raise ResultValidationError(f"Falta la salida bruta: {raw_file}")
    return {"manifest": manifest, "system": system, "results": results}
