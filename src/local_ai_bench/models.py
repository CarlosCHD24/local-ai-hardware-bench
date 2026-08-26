from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from .errors import PreparationError

VERIFY_CACHE = ".verified.json"


def selected_models(
    manifest: dict[str, Any], suite_model_ids: list[str], requested: Iterable[str] | None = None
) -> list[dict[str, Any]]:
    by_id = {model["id"]: model for model in manifest["models"]}
    ids = list(requested or suite_model_ids)
    if len(set(ids)) != len(ids):
        raise PreparationError("La selección contiene modelos duplicados")
    unknown = [model_id for model_id in ids if model_id not in by_id]
    if unknown:
        raise PreparationError(f"Modelos desconocidos: {', '.join(unknown)}")
    return [by_id[model_id] for model_id in ids]


def model_dir(home: Path, model: dict[str, Any]) -> Path:
    return home / "models" / model["id"]


def model_primary_path(home: Path, model: dict[str, Any]) -> Path:
    return model_dir(home, model) / model["primary_artifact"]


def prepare_models(home: Path, models: list[dict[str, Any]]) -> None:
    missing_bytes = sum(
        artifact["size_bytes"]
        for model in models
        for artifact in model["artifacts"]
        if not (model_dir(home, model) / artifact["filename"]).is_file()
    )
    home.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(home).free
    if missing_bytes and free < int(missing_bytes * 1.05):
        raise PreparationError(
            f"Espacio insuficiente: se necesitan aproximadamente {format_bytes(missing_bytes)} "
            f"y hay {format_bytes(free)} disponibles"
        )

    for model in models:
        directory = model_dir(home, model)
        directory.mkdir(parents=True, exist_ok=True)
        for artifact in model["artifacts"]:
            destination = directory / artifact["filename"]
            if artifact_verified(destination, artifact, directory / VERIFY_CACHE):
                print(f"✓ {artifact['filename']} ya está verificado")
                continue
            download(artifact["url"], destination, artifact["size_bytes"])
            verify_artifact(destination, artifact)
            update_verify_cache(directory, artifact)
            print(f"✓ {artifact['filename']} verificado")


def artifact_verified(destination: Path, artifact: dict[str, Any], cache_path: Path) -> bool:
    if not destination.is_file() or destination.stat().st_size != artifact["size_bytes"]:
        return False
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    entry = cache.get(artifact["filename"], {})
    stat = destination.stat()
    return (
        entry.get("sha256") == artifact["sha256"]
        and entry.get("size_bytes") == stat.st_size
        and entry.get("mtime_ns") == stat.st_mtime_ns
    )


def update_verify_cache(directory: Path, artifact: dict[str, Any]) -> None:
    cache_path = directory / VERIFY_CACHE
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}
    stat = (directory / artifact["filename"]).stat()
    cache[artifact["filename"]] = {
        "sha256": artifact["sha256"],
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }
    cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_artifact(path: Path, artifact: dict[str, Any]) -> None:
    actual_size = path.stat().st_size
    if actual_size != artifact["size_bytes"]:
        raise PreparationError(
            f"Tamaño incorrecto para {path.name}: {actual_size}, esperado {artifact['size_bytes']}"
        )
    digest = sha256_file(path)
    if digest != artifact["sha256"]:
        raise PreparationError(
            f"SHA-256 incorrecto para {path.name}: {digest}, esperado {artifact['sha256']}"
        )


def verify_model(home: Path, model: dict[str, Any], force_hash: bool = False) -> None:
    directory = model_dir(home, model)
    for artifact in model["artifacts"]:
        path = directory / artifact["filename"]
        if not path.is_file():
            raise PreparationError(f"Falta el modelo {path}; ejecuta prepare")
        if force_hash or not artifact_verified(path, artifact, directory / VERIFY_CACHE):
            verify_artifact(path, artifact)
            update_verify_cache(directory, artifact)


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path, expected_size: int) -> None:
    partial = destination.with_suffix(destination.suffix + ".part")
    existing = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "local-ai-hardware-bench/0.1"}
    if 0 < existing < expected_size:
        headers["Range"] = f"bytes={existing}-"
    elif existing >= expected_size:
        partial.unlink()
        existing = 0

    request = urllib.request.Request(url, headers=headers)
    print(f"↓ {destination.name} ({format_bytes(expected_size)})")
    try:
        response = urllib.request.urlopen(request, timeout=60)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise PreparationError(f"No se pudo descargar {destination.name}: {exc}") from exc

    append = existing > 0 and getattr(response, "status", None) == 206
    if not append:
        existing = 0
    mode = "ab" if append else "wb"
    downloaded = existing
    next_report = downloaded
    try:
        with response, partial.open(mode) as handle:
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
                downloaded += len(chunk)
                if downloaded >= next_report:
                    percent = min(100.0, downloaded * 100 / expected_size)
                    print(
                        f"\r  {percent:5.1f}%  {format_bytes(downloaded)} / {format_bytes(expected_size)}",
                        end="",
                        file=sys.stderr,
                        flush=True,
                    )
                    next_report = downloaded + 64 * 1024 * 1024
    except (OSError, urllib.error.URLError) as exc:
        raise PreparationError(f"Descarga interrumpida de {destination.name}: {exc}") from exc
    print(file=sys.stderr)
    os.replace(partial, destination)


def format_bytes(value: int | float | None) -> str:
    if value is None:
        return "desconocido"
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TiB"
