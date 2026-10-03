"""Comprobación de sólo lectura de listeners TCP en loopback.

Lee ``/proc/net/tcp`` (sólo stdlib, sin dependencias externas) y verifica que
las direcciones ``host:puerto`` solicitadas estén en estado ``LISTEN``.

Uso::

    python3 monitoring/check_listeners.py --require 127.0.0.1:9100,127.0.0.1:9090

Devuelve 0 si todos los listeners están presentes y 1 si falta alguno.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

#: Estado TCP ``LISTEN`` en el formato de ``/proc/net/tcp``.
LISTEN_STATE = "0A"
DEFAULT_PROC = "/proc/net/tcp"


@dataclass(frozen=True)
class ListenerResult:
    """Resultado por cada dirección solicitada."""

    address: str
    present: bool
    required: bool = True

    @property
    def status(self) -> str:
        return "ok" if self.present else "error"

    @property
    def message(self) -> str:
        if self.present:
            return f"listener {self.address}: presente"
        return f"listener {self.address}: falta"

    def as_dict(self) -> dict:
        return {
            "name": f"listener:{self.address}",
            "status": self.status,
            "required": self.required,
            "present": self.present,
            "message": self.message,
        }


def _decode_ipv4(value: str) -> str | None:
    """Convierte una dirección IPv4 de ``/proc/net/tcp`` (hex LE) a notación punto."""
    if len(value) != 8:
        return None
    try:
        octets = [int(value[i : i + 2], 16) for i in range(0, 8, 2)]
    except ValueError:
        return None
    return ".".join(str(octet) for octet in reversed(octets))


def canonical_endpoint(value: str) -> str:
    """Normaliza ``host:puerto``; si no es parseable, devuelve el texto tal cual."""
    host, separator, port = value.rpartition(":")
    if not separator:
        return value.strip()
    host = host.strip()
    port = port.strip()
    if not port.isdigit():
        return value.strip()
    return f"{host}:{int(port)}"


def parse_requirements(spec: str) -> list[str]:
    """Divide una lista separada por comas, ignorando elementos vacíos."""
    return [canonical_endpoint(item) for item in spec.split(",") if item.strip()]


def parse_proc_net_tcp(text: str) -> set[str]:
    """Extrae las direcciones locales en estado ``LISTEN`` de ``/proc/net/tcp``."""
    listeners: set[str] = set()
    for line in text.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 4:
            continue
        local_address, state = fields[1], fields[3]
        if state.upper() != LISTEN_STATE:
            continue
        address_hex, separator, port_hex = local_address.partition(":")
        if not separator:
            continue
        ip = _decode_ipv4(address_hex)
        if ip is None:
            continue
        try:
            port = int(port_hex, 16)
        except ValueError:
            continue
        listeners.add(f"{ip}:{port}")
    return listeners


def list_listeners(path: str | Path = DEFAULT_PROC) -> set[str]:
    """Lee el fichero ``path`` y devuelve los listeners en escucha."""
    return parse_proc_net_tcp(Path(path).read_text(encoding="utf-8"))


def evaluate(required: list[str], present: set[str]) -> list[ListenerResult]:
    """Compara los listeners requeridos con los presentes, preservando el orden."""
    return [ListenerResult(item, item in present) for item in required]


def check(
    required: list[str], path: str | Path = DEFAULT_PROC
) -> list[ListenerResult]:
    """Ejecuta la comprobación leyendo ``path``."""
    return evaluate(required, list_listeners(path))


def exit_code(results: list[ListenerResult]) -> int:
    return 1 if any(not result.present for result in results) else 0


def render_text(results: list[ListenerResult], code: int) -> str:
    lines = [f"[{result.status.upper()}] {result.message}" for result in results]
    lines.append(f"listeners={len(results)} exit={code}")
    return "\n".join(lines)


def render_json(results: list[ListenerResult], code: int) -> str:
    return json.dumps(
        {
            "ok": code == 0,
            "exit_code": code,
            "listeners": [result.as_dict() for result in results],
        },
        indent=2,
        sort_keys=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require",
        default="",
        help="lista de host:puerto separada por comas",
    )
    parser.add_argument(
        "--proc",
        default=DEFAULT_PROC,
        help="ruta alternativa a /proc/net/tcp (por defecto: %(default)s)",
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
    required = parse_requirements(args.require)
    try:
        present = list_listeners(args.proc)
    except OSError as exc:
        print(f"warning: no se pudo leer {args.proc}: {exc}", file=sys.stderr)
        present = set()
    results = evaluate(required, present)
    code = exit_code(results)
    if args.as_json:
        print(render_json(results, code))
    else:
        print(render_text(results, code))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
