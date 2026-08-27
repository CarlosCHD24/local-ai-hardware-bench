from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ConfigError
from .paths import project_root, suite_path

ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class LoadedConfig:
    suite: dict[str, Any]
    manifest: dict[str, Any]
    suite_file: Path
    manifest_file: Path

    @property
    def models_by_id(self) -> dict[str, dict[str, Any]]:
        return {model["id"]: model for model in self.manifest["models"]}


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"No existe el archivo de configuración: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON no válido en {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigError(f"La raíz de {path} debe ser un objeto JSON")
    return value


def load_config(suite: str = "quick-v1", root: Path | None = None) -> LoadedConfig:
    root = root or project_root()
    suite_file = suite_path(suite, root)
    suite_data = read_json(suite_file)
    manifest_file = root / "models" / str(suite_data.get("model_manifest", ""))
    manifest_data = read_json(manifest_file)
    validate_suite(suite_data, manifest_data)
    return LoadedConfig(suite_data, manifest_data, suite_file, manifest_file)


def validate_suite(suite: dict[str, Any], manifest: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "id",
        "runtime",
        "model_manifest",
        "models",
        "scenarios",
        "repetitions",
        "warmup_runs",
    }
    missing = sorted(required - suite.keys())
    if missing:
        raise ConfigError(f"Faltan campos en la suite: {', '.join(missing)}")
    if suite["schema_version"] != 1:
        raise ConfigError("Solo se admite schema_version=1")
    if not ID_PATTERN.fullmatch(str(suite["id"])):
        raise ConfigError(f"Identificador de suite no válido: {suite['id']}")

    runtime = suite["runtime"]
    if not isinstance(runtime, dict):
        raise ConfigError("runtime debe ser un objeto")
    for field in ("id", "repository", "revision", "binary", "gpu_layers"):
        if field not in runtime:
            raise ConfigError(f"Falta runtime.{field}")
    if not REVISION_PATTERN.fullmatch(str(runtime["revision"])):
        raise ConfigError("runtime.revision debe ser un commit Git de 40 caracteres")

    if not isinstance(suite["repetitions"], int) or suite["repetitions"] < 1:
        raise ConfigError("repetitions debe ser un entero positivo")
    if not isinstance(suite["warmup_runs"], int) or suite["warmup_runs"] < 0:
        raise ConfigError("warmup_runs debe ser un entero no negativo")
    timeout = suite.get("timeout_seconds")
    if timeout is not None and (not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 1):
        raise ConfigError("timeout_seconds debe ser un entero positivo")
    model_budget = suite.get("model_time_budget_seconds")
    if model_budget is not None and (
        not isinstance(model_budget, int) or isinstance(model_budget, bool) or model_budget < 1
    ):
        raise ConfigError("model_time_budget_seconds debe ser un entero positivo")
    cooldown = suite.get("cooldown_seconds")
    if cooldown is not None and (
        not isinstance(cooldown, (int, float))
        or isinstance(cooldown, bool)
        or cooldown < 0
        or cooldown > 60
    ):
        raise ConfigError("cooldown_seconds debe estar entre 0 y 60")
    for field in (
        "skip_remaining_after_memory_failure",
        "skip_remaining_after_capacity_failure",
    ):
        if field in suite and not isinstance(suite[field], bool):
            raise ConfigError(f"{field} debe ser booleano")
    if not suite["models"] or not isinstance(suite["models"], list):
        raise ConfigError("La suite debe contener al menos un modelo")
    if len(set(suite["models"])) != len(suite["models"]):
        raise ConfigError("La suite contiene modelos duplicados")
    if not suite["scenarios"] or not isinstance(suite["scenarios"], list):
        raise ConfigError("La suite debe contener al menos un escenario")

    profiles = suite.get("profiles", [])
    if profiles and not isinstance(profiles, list):
        raise ConfigError("profiles debe ser una lista")
    profile_ids: set[str] = set()
    for profile in profiles:
        if not isinstance(profile, dict) or not ID_PATTERN.fullmatch(str(profile.get("id", ""))):
            raise ConfigError("Cada perfil debe tener un id válido")
        if profile["id"] in profile_ids:
            raise ConfigError(f"Perfil duplicado: {profile['id']}")
        profile_ids.add(profile["id"])
        for field in ("gpu_layers", "fit_target_mib", "fit_context"):
            value = profile.get(field)
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ConfigError(f"profiles[].{field} debe ser un entero no negativo")
        if profile.get("fit_target_mib") is not None and "gpu_layers" in profile:
            raise ConfigError("Un perfil no puede combinar fit_target_mib y gpu_layers")
        if "cuda_unified_memory" in profile and not isinstance(profile["cuda_unified_memory"], bool):
            raise ConfigError("profiles[].cuda_unified_memory debe ser booleano")
        backends = profile.get("backends")
        if backends is not None:
            allowed_backends = {"cpu", "cuda", "metal", "vulkan"}
            if (
                not isinstance(backends, list)
                or not backends
                or any(not isinstance(backend, str) for backend in backends)
                or any(backend not in allowed_backends for backend in backends)
                or len(set(backends)) != len(backends)
            ):
                raise ConfigError(
                    "profiles[].backends debe contener backends válidos y no duplicados"
                )

    monitoring = suite.get("memory_monitoring")
    if monitoring is not None:
        if not isinstance(monitoring, dict):
            raise ConfigError("memory_monitoring debe ser un objeto")
        interval = monitoring.get("interval_ms", 1000)
        if not isinstance(interval, int) or interval < 200:
            raise ConfigError("memory_monitoring.interval_ms debe ser al menos 200")
        max_swap = monitoring.get("max_swap_growth_bytes")
        if max_swap is not None and (not isinstance(max_swap, int) or max_swap < 1):
            raise ConfigError("memory_monitoring.max_swap_growth_bytes debe ser positivo")
        minimum = monitoring.get("min_available_percent")
        if minimum is not None and (
            not isinstance(minimum, (int, float)) or isinstance(minimum, bool) or minimum < 0 or minimum > 100
        ):
            raise ConfigError("memory_monitoring.min_available_percent debe estar entre 0 y 100")

    scenario_ids: set[str] = set()
    for scenario in suite["scenarios"]:
        for field in ("id", "prompt_tokens", "generated_tokens"):
            if field not in scenario:
                raise ConfigError(f"Falta scenarios[].{field}")
        if scenario["id"] in scenario_ids:
            raise ConfigError(f"Escenario duplicado: {scenario['id']}")
        scenario_ids.add(scenario["id"])
        prompt = scenario["prompt_tokens"]
        generated = scenario["generated_tokens"]
        if not isinstance(prompt, int) or not isinstance(generated, int):
            raise ConfigError("Los tamaños de escenario deben ser enteros")
        if prompt < 0 or generated < 0 or prompt + generated == 0:
            raise ConfigError(f"Escenario vacío o negativo: {scenario['id']}")

    validate_manifest(manifest)
    known_models = {model["id"] for model in manifest["models"]}
    unknown = sorted(set(suite["models"]) - known_models)
    if unknown:
        raise ConfigError(f"Modelos no definidos en el manifiesto: {', '.join(unknown)}")


def validate_manifest(manifest: dict[str, Any]) -> None:
    for field in ("schema_version", "id", "family", "quantization", "license", "models"):
        if field not in manifest:
            raise ConfigError(f"Falta el campo del manifiesto: {field}")
    if manifest["schema_version"] != 1:
        raise ConfigError("Solo se admite schema_version=1 en el manifiesto")
    if not isinstance(manifest["models"], list) or not manifest["models"]:
        raise ConfigError("El manifiesto debe contener modelos")

    model_ids: set[str] = set()
    for model in manifest["models"]:
        for field in ("id", "repository", "revision", "primary_artifact", "artifacts"):
            if field not in model:
                raise ConfigError(f"Falta models[].{field}")
        if model["id"] in model_ids:
            raise ConfigError(f"Modelo duplicado: {model['id']}")
        model_ids.add(model["id"])
        if not REVISION_PATTERN.fullmatch(str(model["revision"])):
            raise ConfigError(f"Revisión no válida para {model['id']}")
        filenames = {artifact.get("filename") for artifact in model["artifacts"]}
        if model["primary_artifact"] not in filenames:
            raise ConfigError(f"primary_artifact no aparece en {model['id']}")
        for artifact in model["artifacts"]:
            for field in ("filename", "url", "size_bytes", "sha256"):
                if field not in artifact:
                    raise ConfigError(f"Falta artifact.{field} en {model['id']}")
            if not isinstance(artifact["size_bytes"], int) or artifact["size_bytes"] < 1:
                raise ConfigError(f"Tamaño no válido en {artifact['filename']}")
            if not SHA256_PATTERN.fullmatch(str(artifact["sha256"])):
                raise ConfigError(f"SHA-256 no válido en {artifact['filename']}")


def selected_profiles(
    suite: dict[str, Any], requested: list[str] | None = None, backend: str | None = None
) -> list[dict[str, Any]]:
    profiles = suite.get("profiles") or [{"id": "default"}]
    by_id = {profile["id"]: profile for profile in profiles}
    ids = requested or list(by_id)
    unknown = [profile_id for profile_id in ids if profile_id not in by_id]
    if unknown:
        raise ConfigError(f"Perfiles desconocidos: {', '.join(unknown)}")
    if len(set(ids)) != len(ids):
        raise ConfigError("La selección contiene perfiles duplicados")
    selected = [by_id[profile_id] for profile_id in ids]
    if backend is None:
        return selected
    compatible = [
        profile
        for profile in selected
        if not profile.get("backends") or backend in profile["backends"]
    ]
    if requested and len(compatible) != len(selected):
        incompatible = [profile["id"] for profile in selected if profile not in compatible]
        raise ConfigError(
            f"Perfiles no compatibles con el backend {backend}: {', '.join(incompatible)}"
        )
    if not compatible:
        raise ConfigError(f"La suite no tiene perfiles compatibles con el backend {backend}")
    return compatible


def validate_system_id(system_id: str) -> str:
    if not ID_PATTERN.fullmatch(system_id):
        raise ConfigError(
            "system-id debe tener entre 2 y 64 caracteres y usar solo letras, "
            "números, puntos, guiones o guiones bajos"
        )
    return system_id
