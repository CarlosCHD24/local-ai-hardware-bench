from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .config import load_config, selected_profiles, validate_system_id
from .errors import BenchError
from .models import format_bytes, model_dir, prepare_models, selected_models
from .paths import data_home, project_root
from .report import compare_runs, write_report
from .runner import execute_suite
from .runtimes.llamacpp import LlamaCppRuntime, find_llama_bench
from .system import detect_backend, doctor_checks
from .validate import validate_result_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local-ai-bench",
        description="Benchmark reproducible de hardware para inferencia local.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--project-root", type=Path, help="Raíz del proyecto (normalmente se detecta)")
    parser.add_argument("--home", type=Path, help="Directorio para runtimes y modelos")
    parser.add_argument("--suite", default="quick-v1", help="ID o ruta de la suite")

    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Comprobar plataforma y dependencias")
    _backend_argument(doctor)
    doctor.add_argument("--runtime-binary", type=Path)
    doctor.add_argument("--json", action="store_true", help="Emitir JSON")

    prepare = subparsers.add_parser("prepare", help="Compilar el runtime y descargar modelos")
    _backend_argument(prepare)
    prepare.add_argument("--runtime-binary", type=Path, help="Usar un llama-bench ya instalado")
    prepare.add_argument("--model", action="append", dest="models", help="Preparar solo este modelo")
    prepare.add_argument("--skip-runtime", action="store_true")
    prepare.add_argument("--skip-models", action="store_true")
    prepare.add_argument("--jobs", type=int, help="Procesos paralelos de compilación")
    prepare.add_argument("--yes", action="store_true", help="Confirmar descargas sin preguntar")

    run = subparsers.add_parser("run", help="Ejecutar una suite ya preparada")
    _backend_argument(run)
    run.add_argument("--system-id", required=True, help="Identificador público y anónimo del equipo")
    run.add_argument("--runtime-binary", type=Path)
    run.add_argument("--model", action="append", dest="models", help="Ejecutar solo este modelo")
    run.add_argument("--profile", action="append", dest="profiles", help="Ejecutar solo este perfil")
    run.add_argument("--threads", type=int, help="Fijar hilos CPU; por defecto decide llama.cpp")
    run.add_argument("--output", type=Path, help="Raíz para resultados")
    run.add_argument("--verify-checksums", action="store_true", help="Recalcular todos los SHA-256")
    run.add_argument("--fail-fast", action="store_true")

    report = subparsers.add_parser("report", help="Regenerar informe Markdown y CSV")
    report.add_argument("run_dir", type=Path)

    compare = subparsers.add_parser("compare", help="Comparar dos o más ejecuciones")
    compare.add_argument("run_dirs", nargs="+", type=Path)
    compare.add_argument("--output", type=Path)

    validate = subparsers.add_parser("validate", help="Validar una ejecución publicada")
    validate.add_argument("run_dir", type=Path)
    return parser


def _backend_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--backend",
        choices=("auto", "cpu", "cuda", "metal", "vulkan"),
        default="auto",
        help="Backend de llama.cpp (por defecto: detección automática)",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return dispatch(args)
    except BenchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nOperación cancelada.", file=sys.stderr)
        return 130


def dispatch(args: argparse.Namespace) -> int:
    root = (args.project_root or project_root()).expanduser().resolve()
    home = (args.home or data_home(root)).expanduser().resolve()

    if args.command in {"report", "compare", "validate"}:
        return _result_command(args)

    config = load_config(args.suite, root)
    backend = detect_backend(args.backend)
    binary_override = args.runtime_binary.expanduser().resolve() if args.runtime_binary else None
    runtime = LlamaCppRuntime(config.suite["runtime"], home, backend, binary_override, getattr(args, "jobs", None))

    if args.command == "doctor":
        candidate = binary_override or find_llama_bench(home, backend)
        checks = doctor_checks(backend, candidate)
        if args.json:
            print(json.dumps({"backend": backend, "checks": checks}, indent=2))
        else:
            print(f"Backend seleccionado: {backend}")
            for check in checks:
                mark = "✓" if check["ok"] else "✗"
                print(f"{mark} {check['name']}: {check.get('value') or 'no disponible'}")
        return 0 if all(check["ok"] for check in checks) else 1

    models = selected_models(config.manifest, config.suite["models"], getattr(args, "models", None))
    if args.command == "prepare":
        if args.jobs is not None and args.jobs < 1:
            raise BenchError("--jobs debe ser positivo")
        if not args.skip_runtime:
            print(f"Preparando llama.cpp ({backend})…")
            binary = runtime.prepare()
            print(f"✓ Runtime preparado: {binary}")
        if not args.skip_models:
            _confirm_download(home, models, args.yes)
            prepare_models(home, models)
        print("Preparación completada.")
        return 0

    if args.command == "run":
        system_id = validate_system_id(args.system_id)
        if args.threads is not None and args.threads < 1:
            raise BenchError("--threads debe ser positivo")
        output = (args.output or root / "results").expanduser().resolve()
        run_dir = execute_suite(
            config,
            runtime,
            home,
            output,
            system_id,
            models,
            threads=args.threads,
            force_hash=args.verify_checksums,
            fail_fast=args.fail_fast,
            profiles=selected_profiles(config.suite, args.profiles),
        )
        print(f"\nResultado: {run_dir}")
        print(f"Informe: {run_dir / 'report.md'}")
        return 0
    raise BenchError(f"Comando no implementado: {args.command}")


def _result_command(args: argparse.Namespace) -> int:
    if args.command == "validate":
        data = validate_result_dir(args.run_dir)
        count = len(data["results"].get("results", []))
        print(f"✓ Resultado válido: {count} pruebas")
        return 0
    if args.command == "report":
        report, csv_path = write_report(args.run_dir)
        print(f"✓ {report}")
        print(f"✓ {csv_path}")
        return 0
    if args.command == "compare":
        text = compare_runs(args.run_dirs)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(f"✓ {args.output}")
        else:
            print(text, end="")
        return 0
    raise BenchError(f"Comando no implementado: {args.command}")


def _confirm_download(home: Path, models: list[dict[str, Any]], assume_yes: bool) -> None:
    missing = [
        artifact
        for model in models
        for artifact in model["artifacts"]
        if not (model_dir(home, model) / artifact["filename"]).is_file()
    ]
    total = sum(artifact["size_bytes"] for artifact in missing)
    if not missing:
        return
    print(f"Se descargarán {len(missing)} archivos ({format_bytes(total)}) en {home / 'models'}.")
    if assume_yes:
        return
    if not sys.stdin.isatty():
        raise BenchError("La descarga requiere confirmación; repite con --yes")
    answer = input("¿Continuar? [y/N] ").strip().lower()
    if answer not in {"y", "yes", "s", "sí", "si"}:
        raise BenchError("Descarga cancelada")


if __name__ == "__main__":
    raise SystemExit(main())
