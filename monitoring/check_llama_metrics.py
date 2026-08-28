#!/usr/bin/env python3
"""Comprobador seguro de métricas de llama-server."""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


METRICS_CATALOG = frozenset([
    "llamacpp:prompt_tokens_total",
    "llamacpp:prompt_tokens_cached_total",
    "llamacpp:tokens_predicted_total",
    "llamacpp:prompt_seconds_total",
    "llamacpp:tokens_predicted_seconds_total",
    "llamacpp:prompt_tokens_seconds",
    "llamacpp:predicted_tokens_seconds",
    "llamacpp:requests_processing",
    "llamacpp:requests_deferred",
    "llamacpp:n_tokens_max",
])


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Validar endpoints /health y /metrics de llama-server"
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8080",
        help="URL base del servidor (default: http://127.0.0.1:8080)"
    )
    parser.add_argument(
        "--api-key-file",
        help="Archivo con la clave API"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=7.0,
        help="Timeout en segundos (default: 7.0)"
    )
    return parser.parse_args(argv)


def get_api_key(base_url, api_key_file):
    """Obtener la clave API del archivo o variable de entorno."""
    if api_key_file:
        try:
            with open(api_key_file, "r") as f:
                key = f.read().strip()
                if not key:
                    sys.stderr.write("Clave API vacía en archivo\n")
                    return None
                return key
        except OSError as e:
            sys.stderr.write(f"No se pudo leer {api_key_file}: {e}\n")
            return None
    else:
        key = os.environ.get("LOCAL_AI_API_KEY")
        if not key:
            sys.stderr.write("Clave API no encontrada (archivo o variable de entorno)\n")
            return None
        return key


def check_health(base_url, timeout, api_key):
    """Validar endpoint /health. Devuelve (ok, error_msg)."""
    url = base_url.rstrip("/") + "/health"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status < 200 or response.status >= 300:
                return False, f"HTTP {response.status}"

            body = response.read().decode("utf-8")
            try:
                data = json.loads(body)
                if data.get("status") != "ok":
                    return False, f"status != 'ok': {data.get('status')}"
                return True, None
            except json.JSONDecodeError:
                return False, "JSON inválido"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return False, f"Fallo de red: {e.reason}"
    except Exception:
        return False, "Error inesperado"


def check_metrics(base_url, timeout, api_key):
    """Validar endpoint /metrics. Devuelve (ok, missing_metrics)."""
    url = base_url.rstrip("/") + "/metrics"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status < 200 or response.status >= 300:
                return False, None

            body = response.read().decode("utf-8")
            found = set()

            for line in body.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                metric_name = line.split()[0].split("{")[0]
                found.add(metric_name)

            missing = METRICS_CATALOG - found
            if missing:
                return False, sorted(missing)
            return True, None
    except urllib.error.HTTPError as e:
        return False, None
    except urllib.error.URLError as e:
        return False, None
    except Exception as e:
        return False, None


def main(argv=None):
    args = parse_args(argv)

    # Validar timeout positivo
    if args.timeout <= 0:
        sys.stderr.write("Timeout debe ser positivo\n")
        return 2

    # Obtener clave API
    api_key = get_api_key(args.base_url, args.api_key_file)
    if api_key is None:
        return 2

    # Validar health
    health_ok, health_err = check_health(args.base_url, args.timeout, api_key)
    if not health_ok:
        sys.stderr.write(f"/health: {health_err}\n")
        return 3

    # Validar metrics
    metrics_ok, missing = check_metrics(args.base_url, args.timeout, api_key)
    if not metrics_ok:
        if missing:
            sys.stderr.write(f"/metrics: faltan métricas: {', '.join(missing)}\n")
            return 4
        else:
            sys.stderr.write("/metrics: fallo de red o HTTP\n")
            return 3

    sys.stdout.write("OK: health y metrics válidos\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
