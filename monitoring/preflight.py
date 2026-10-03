"""Preflight de sólo lectura para un host de monitoring local."""
from __future__ import annotations
import shutil

REQUIRED = ("systemctl", "nvidia-smi")

def main() -> int:
    missing = [name for name in REQUIRED if shutil.which(name) is None]
    if missing:
        print("missing: " + ", ".join(missing))
        return 1
    print("OK: prerequisites available")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
