"""Comprueba artefactos operativos de monitoring sin ejecutar systemd."""
from pathlib import Path

ROOT = Path(__file__).parent

def main() -> int:
    service = (ROOT / "systemd/local-ai-nvidia-metrics.service").read_text()
    timer = (ROOT / "systemd/local-ai-nvidia-metrics.timer").read_text()
    required = ("nvidia_textfile", "/var/lib/node_exporter/textfile_collector", "OnUnitActiveSec=15s", "RandomizedDelaySec=0", "Persistent=true")
    return 0 if all(item in service + timer for item in required) else 1

if __name__ == "__main__":
    raise SystemExit(main())
