"""Validador mínimo del contrato de configuración Prometheus local."""
from __future__ import annotations
import argparse
from pathlib import Path

REQUIRED = ("scrape_interval: 15s", "recording-rules.yml", "alert-rules.yml", "job_name: local-ai-server", "job_name: node-exporter", "192.168.3.42:8080", "127.0.0.1:9100", "metrics_path: /metrics", "bearer_token_file:")

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    path = Path(args.config)
    if not path.is_file(): return 2
    text = path.read_text(encoding="utf-8")
    return 0 if all(item in text for item in REQUIRED) and "Bearer " not in text else 1

if __name__ == "__main__":
    raise SystemExit(main())
