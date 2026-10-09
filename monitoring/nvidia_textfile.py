"""Escribe una muestra NVIDIA para el textfile collector de node_exporter."""
from __future__ import annotations
import argparse
import contextlib
import io
import os
from pathlib import Path
from monitoring import nvidia_metrics

NAME = "local_ai_nvidia.prom"

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True)
    parser.add_argument("--timeout", type=float, default=5)
    args = parser.parse_args(argv)
    directory = Path(args.directory)
    if args.timeout <= 0 or not directory.is_dir():
        return 2
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(io.StringIO()):
        code = nvidia_metrics.main(["--timeout", str(args.timeout)])
    content = captured.getvalue() if code == 0 else "local_ai_gpu_scrape_success 0\n"
    target = directory / NAME
    temporary = directory / f".{NAME}.tmp"
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, target)
    except OSError:
        try: temporary.unlink()
        except FileNotFoundError: pass
        return 2
    return 0 if code == 0 else 3

if __name__ == "__main__":
    raise SystemExit(main())
