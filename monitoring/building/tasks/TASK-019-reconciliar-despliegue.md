# TASK-019: Reconciliar documentación y despliegue

| Campo | Valor |
|---|---|
| Status | `review` |
| Owner | — |
| Created | 2026-08-29T22:30:00Z |
| Updated | 2026-10-03T21:35:24Z |
| Depends on | TASK-018 |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s |
| Rounds | 3 |
| Contract tests | `monitoring.taskctl validate` |
| Working directory | Repository root |

## Objetivo

Actualizar la documentación para reflejar el stack desplegado, sus listeners
locales, retención de 30 días, usuario del colector y procedimiento de acceso
por túnel SSH; no incluir secretos ni contraseñas.

## Handoff

Entregado a `review` (pendiente de aprobación del orquestador).

Cambios:

- `monitoring/deployment.md` reescrito para reflejar los artefactos reales:
  listeners, usuarios, retención y túnel SSH.
- `monitoring/building/tasks/TASK-019-reconciliar-despliegue.md` y
  `monitoring/building/TASKS.md`: estado a `review`.

Verificaciones y hechos contrastados:

- `User=prometheus` en `systemd/node-exporter.service`; `User=carlos` y
  `Group=prometheus` en `systemd/local-ai-nvidia-metrics.service`.
- `127.0.0.1:9100` versionado en `node-exporter.service` y `prometheus.yml`.
- `127.0.0.1:9090` sólo aparece como URL de la fuente Grafana: no hay unidad
  systemd de Prometheus, por lo que se documenta como requisito.
- `127.0.0.1:3000` no aparece en ningún artefacto: se documenta como requisito
  de loopback de Grafana.
- Retención de 30 días: sólo declarada en `README.md` (4.1/13), sin
  `--storage.tsdb.retention.time` en artefactos; documentada como requisito.
- IP `192.168.3.42`: inventariada como `desktop-ai` (servidor de inferencia) y
  sujeta a DHCP; no se modifica en `prometheus.yml`.
- Herramientas nuevas documentadas: `preflight.py` (`--profile`, `--json`,
  `--require-listeners`, `--textfile-dir`), `check_listeners.py` y
  `check_nvidia_textfile.py`.
- `.venv/bin/python -m monitoring.taskctl validate --root .` -> `OK: 24 tasks`
  (exit 0). El literal `.venv/bin/python monitoring/taskctl.py --help` falla
  con `ModuleNotFoundError: No module named 'monitoring'`; el contrato
  `monitoring.taskctl` debe invocarse como módulo (`-m`). No se tocó
  `taskctl.py`.
- No se modificaron `monitoring/contract_tests/`, el servidor remoto ni
  claves.
