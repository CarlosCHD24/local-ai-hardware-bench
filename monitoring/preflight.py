"""Preflight de sólo lectura para un host de monitoring local.

Perfiles disponibles:

``dev``
    Host de desarrollo. ``systemctl`` es obligatorio; la ausencia de
    ``nvidia-smi`` (por ejemplo, una máquina sin GPU) se reporta como
    ``WARNING`` y no altera el código de salida.
``server``
    Host de despliegue. Todas las comprobaciones son obligatorias y cualquier
    fallo devuelve un código de salida distinto de cero.

El script nunca escribe ni modifica el sistema: sólo consulta el ``PATH``.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

try:  # import como paquete (tests, `python -m monitoring.preflight`)
    from monitoring import (
        check_listeners,
        check_nvidia_textfile,
        validate_operation,
        validate_prometheus,
    )
except ImportError:  # pragma: no cover - ejecución directa `python monitoring/preflight.py`
    import check_listeners  # type: ignore
    import check_nvidia_textfile  # type: ignore
    import validate_operation  # type: ignore
    import validate_prometheus  # type: ignore

PROFILES = ("dev", "server")
DEFAULT_PROFILE = "server"

MONITORING_ROOT = Path(__file__).resolve().parent
PROMETHEUS_CONFIG = MONITORING_ROOT / "prometheus" / "prometheus.yml"
SYSTEMD_UNITS = sorted((MONITORING_ROOT / "systemd").glob("*.service")) + sorted(
    (MONITORING_ROOT / "systemd").glob("*.timer")
)

Which = Callable[[str], "str | None"]
Runner = Callable[..., "subprocess.CompletedProcess"]


@dataclass(frozen=True)
class CheckResult:
    """Resultado individual de una comprobación."""

    name: str
    ok: bool
    required: bool
    message: str
    tool: str | None = None

    @property
    def status(self) -> str:
        """``ok``, ``warning`` (fallo no bloqueante) o ``error`` (bloqueante)."""
        if self.ok:
            return "ok"
        return "error" if self.required else "warning"

    def as_dict(self) -> dict:
        data = {
            "name": self.name,
            "status": self.status,
            "required": self.required,
            "message": self.message,
        }
        if self.tool is not None:
            data["tool"] = self.tool
        return data


def _binary_check(name: str, required: bool, which: Which) -> CheckResult:
    found = which(name)
    if found:
        return CheckResult(name, True, required, f"{name}: disponible en {found}")
    return CheckResult(name, False, required, f"{name}: no encontrado en PATH")


def validator_checks() -> list[CheckResult]:
    """Valida artefactos versionados importando los validadores existentes."""
    checks: list[CheckResult] = []
    try:
        code = validate_prometheus.main(["--config", str(PROMETHEUS_CONFIG)])
        checks.append(
            CheckResult(
                "validate_prometheus",
                code == 0,
                True,
                f"validate_prometheus: {PROMETHEUS_CONFIG.name} "
                f"{'valido' if code == 0 else f'invalido (exit {code})'}",
            )
        )
    except Exception as exc:  # noqa: BLE001 - el preflight nunca debe caer
        checks.append(
            CheckResult(
                "validate_prometheus",
                False,
                True,
                f"validate_prometheus: error al ejecutar: {exc}",
            )
        )
    try:
        code = validate_operation.main()
        checks.append(
            CheckResult(
                "validate_operation",
                code == 0,
                True,
                f"validate_operation: unidades "
                f"{'validas' if code == 0 else f'invalidas (exit {code})'}",
            )
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(
            CheckResult(
                "validate_operation",
                False,
                True,
                f"validate_operation: error al ejecutar: {exc}",
            )
        )
    return checks


def tool_check(
    tool: str,
    args: list[str],
    profile: str,
    which: Which,
    runner: Runner,
) -> CheckResult:
    """Ejecuta una herramienta externa o degrada a warning/error según perfil."""
    executable = which(tool)
    if executable is None:
        required = profile == "server"
        return CheckResult(
            tool,
            False,
            required,
            f"{tool}: no encontrado en PATH",
            tool=tool,
        )
    try:
        completed = runner(
            [executable, *args], capture_output=True, text=True
        )
        code = completed.returncode
        stderr = (completed.stderr or "").strip().splitlines()
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            tool,
            False,
            True,
            f"{tool}: error al ejecutar: {exc}",
            tool=tool,
        )
    ok = code == 0
    # promtool sólo valida el fichero versionado: si está presente y falla,
    # bloquea en ambos perfiles. systemd-analyze depende del host (binarios
    # de producción), por lo que en dev un fallo se degrada a warning.
    required = (profile == "server") or (not ok and tool == "promtool")
    if ok:
        message = f"{tool}: OK"
    else:
        detail = f" ({stderr[0]})" if stderr else ""
        message = f"{tool}: fallo (exit {code}){detail}"
    return CheckResult(tool, ok, required, message, tool=tool)


def listener_checks(
    spec: str, proc_path: str | Path = check_listeners.DEFAULT_PROC
) -> list[CheckResult]:
    """Traduce la lista de listeners requeridos a resultados de preflight."""
    required = check_listeners.parse_requirements(spec)
    try:
        present = check_listeners.list_listeners(proc_path)
    except OSError:
        present = set()
    results = []
    for address in required:
        is_present = address in present
        message = (
            f"listener {address}: presente"
            if is_present
            else f"listener {address}: falta"
        )
        results.append(
            CheckResult(
                name=f"listener:{address}",
                ok=is_present,
                required=True,
                message=message,
            )
        )
    return results


def textfile_checks(
    directory: str | Path,
    max_age: float = check_nvidia_textfile.DEFAULT_MAX_AGE,
    now: float | None = None,
) -> list[CheckResult]:
    """Traduce los resultados del textfile NVIDIA a resultados de preflight."""
    results = check_nvidia_textfile.evaluate(directory, max_age=max_age, now=now)
    return [
        CheckResult(
            name=result.name,
            ok=result.ok,
            required=result.required,
            message=result.message,
        )
        for result in results
    ]


def run_checks(
    profile: str,
    which: Which = shutil.which,
    required_listeners: str | None = None,
    proc_path: str | Path = check_listeners.DEFAULT_PROC,
    textfile_dir: str | Path | None = None,
    textfile_max_age: float = check_nvidia_textfile.DEFAULT_MAX_AGE,
    textfile_now: float | None = None,
    runner: Runner = subprocess.run,
) -> list[CheckResult]:
    """Ejecuta las comprobaciones del perfil solicitado, en orden."""
    nvidia_required = profile == "server"
    checks = [
        _binary_check("systemctl", required=True, which=which),
        _binary_check("nvidia-smi", required=nvidia_required, which=which),
    ]
    checks.extend(validator_checks())
    checks.append(
        tool_check(
            "promtool",
            ["check", "config", str(PROMETHEUS_CONFIG)],
            profile,
            which,
            runner,
        )
    )
    checks.append(
        tool_check(
            "systemd-analyze",
            ["verify", *[str(unit) for unit in SYSTEMD_UNITS]],
            profile,
            which,
            runner,
        )
    )
    if required_listeners:
        checks.extend(listener_checks(required_listeners, proc_path=proc_path))
    if textfile_dir:
        checks.extend(
            textfile_checks(
                textfile_dir, max_age=textfile_max_age, now=textfile_now
            )
        )
    return checks


def exit_code(checks: list[CheckResult]) -> int:
    """Devuelve 1 sólo si alguna comprobación obligatoria ha fallado."""
    return 1 if any(check.status == "error" for check in checks) else 0


def render_text(profile: str, checks: list[CheckResult], code: int) -> str:
    lines = [
        f"[{check.status.upper()}] {check.message}"
        for check in checks
    ]
    lines.append(f"profile={profile} checks={len(checks)} exit={code}")
    return "\n".join(lines)


def render_json(profile: str, checks: list[CheckResult], code: int) -> str:
    return json.dumps(
        {
            "profile": profile,
            "ok": code == 0,
            "exit_code": code,
            "checks": [check.as_dict() for check in checks],
        },
        indent=2,
        sort_keys=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default=DEFAULT_PROFILE,
        help="perfil de preflight (por defecto: %(default)s)",
    )
    parser.add_argument(
        "--require-listeners",
        default=None,
        help="lista de host:puerto separada por comas que debe estar en LISTEN",
    )
    parser.add_argument(
        "--textfile-dir",
        default=None,
        help="directorio del textfile collector NVIDIA a validar (opcional)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="emite el informe como JSON en stdout",
    )
    return parser


def main(
    argv: list[str] | None = None,
    which: Which = shutil.which,
    proc_path: str | Path = check_listeners.DEFAULT_PROC,
    textfile_now: float | None = None,
    runner: Runner = subprocess.run,
) -> int:
    args = build_parser().parse_args(argv)
    checks = run_checks(
        args.profile,
        which=which,
        required_listeners=args.require_listeners,
        proc_path=proc_path,
        textfile_dir=args.textfile_dir,
        textfile_now=textfile_now,
        runner=runner,
    )
    code = exit_code(checks)
    if args.as_json:
        print(render_json(args.profile, checks, code))
    else:
        print(render_text(args.profile, checks, code))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
