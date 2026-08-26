from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..errors import PreparationError
from .base import RuntimeAdapter


class LlamaCppRuntime(RuntimeAdapter):
    def __init__(
        self,
        config: dict[str, Any],
        home: Path,
        backend: str,
        binary_override: Path | None = None,
        jobs: int | None = None,
    ) -> None:
        self.config = config
        self.home = home
        self.backend = backend
        self.binary_override = binary_override.resolve() if binary_override else None
        self.jobs = jobs or max(1, os.cpu_count() or 1)
        self.source_dir = home / "runtimes" / "llama.cpp"
        self.build_dir = self.source_dir / f"build-{backend}"

    @property
    def binary(self) -> Path:
        if self.binary_override:
            return self.binary_override
        return self.build_dir / "bin" / self.config["binary"]

    def prepare(self) -> Path:
        if self.binary_override:
            if not self.binary_override.is_file():
                raise PreparationError(f"No existe el binario indicado: {self.binary_override}")
            return self.binary_override
        self.home.mkdir(parents=True, exist_ok=True)
        self._prepare_source()
        self._build()
        if not self.binary.is_file():
            raise PreparationError(f"La compilación no generó {self.binary}")
        return self.binary

    def _prepare_source(self) -> None:
        revision = self.config["revision"]
        if not (self.source_dir / ".git").is_dir():
            self.source_dir.parent.mkdir(parents=True, exist_ok=True)
            self._run(
                [
                    "git",
                    "clone",
                    "--filter=blob:none",
                    "--no-checkout",
                    self.config["repository"],
                    str(self.source_dir),
                ],
                "No se pudo clonar llama.cpp",
            )
        self._run(
            ["git", "-C", str(self.source_dir), "fetch", "--depth", "1", "origin", revision],
            "No se pudo descargar la revisión fijada de llama.cpp",
        )
        self._run(
            ["git", "-C", str(self.source_dir), "checkout", "--detach", revision],
            "No se pudo activar la revisión fijada de llama.cpp",
        )

    def _build(self) -> None:
        options = [
            "-DLLAMA_BUILD_TESTS=OFF",
            "-DLLAMA_BUILD_EXAMPLES=OFF",
            "-DLLAMA_BUILD_SERVER=OFF",
            "-DLLAMA_BUILD_UI=OFF",
            "-DGGML_NATIVE=ON",
        ]
        if self.backend == "cuda":
            options.append("-DGGML_CUDA=ON")
        elif self.backend == "metal":
            options.append("-DGGML_METAL=ON")
        elif self.backend == "vulkan":
            options.append("-DGGML_VULKAN=ON")

        self._run(
            ["cmake", "-S", str(self.source_dir), "-B", str(self.build_dir), *options],
            "No se pudo configurar llama.cpp",
        )
        self._run(
            [
                "cmake",
                "--build",
                str(self.build_dir),
                "--config",
                "Release",
                "--target",
                "llama-bench",
                "-j",
                str(self.jobs),
            ],
            "No se pudo compilar llama.cpp",
        )

    @staticmethod
    def _run(command: list[str], message: str) -> None:
        try:
            subprocess.run(command, check=True)
        except FileNotFoundError as exc:
            raise PreparationError(f"No se encuentra el comando {command[0]}") from exc
        except subprocess.CalledProcessError as exc:
            raise PreparationError(f"{message} (código {exc.returncode})") from exc

    def command(
        self,
        model_path: Path,
        scenario: dict[str, Any],
        repetitions: int,
        threads: int | None = None,
        profile: dict[str, Any] | None = None,
    ) -> list[str]:
        profile = profile or {}
        command = [
            str(self.binary),
            "-m",
            str(model_path),
            "-p",
            str(scenario["prompt_tokens"]),
            "-n",
            str(scenario["generated_tokens"]),
            "-r",
            str(repetitions),
            "-o",
            "json",
        ]
        if profile.get("verbose"):
            command.append("-v")
        if profile.get("fit_target_mib") is not None:
            command.extend(["-fitt", str(profile["fit_target_mib"])])
            if profile.get("fit_context") is not None:
                command.extend(["-fitc", str(profile["fit_context"])])
        else:
            gpu_layers = profile.get("gpu_layers", self.config["gpu_layers"])
            command.extend(["-ngl", str(gpu_layers if self.backend != "cpu" else 0)])
        if profile.get("load_mode"):
            command.extend(["-lm", str(profile["load_mode"])])
        if threads is not None:
            command.extend(["-t", str(threads)])
        return command

    def environment(self, profile: dict[str, Any] | None = None) -> dict[str, str]:
        environment = os.environ.copy()
        if (profile or {}).get("cuda_unified_memory") and self.backend == "cuda":
            environment["GGML_CUDA_ENABLE_UNIFIED_MEMORY"] = "1"
        return environment

    def parse(self, output: str) -> list[dict[str, Any]]:
        output = output.strip()
        if not output:
            raise ValueError("llama-bench no produjo salida JSON")
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            start = output.find("[")
            end = output.rfind("]")
            if start == -1 or end == -1:
                raise ValueError("No se encontró un array JSON en la salida de llama-bench")
            parsed = json.loads(output[start : end + 1])
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
            raise ValueError("Formato JSON inesperado de llama-bench")
        return parsed


def find_llama_bench(home: Path, backend: str) -> Path | None:
    candidates = [
        home / "runtimes" / "llama.cpp" / f"build-{backend}" / "bin" / "llama-bench",
        home / "runtimes" / "llama.cpp" / "build" / "bin" / "llama-bench",
    ]
    found = shutil.which("llama-bench")
    if found:
        candidates.insert(0, Path(found))
    return next((path.resolve() for path in candidates if path.is_file()), None)
