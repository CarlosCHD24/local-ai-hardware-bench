# TASK-010: Preparar el servicio de node_exporter

| Campo | Valor |
|---|---|
| Status | `done` |
| Owner | — |
| Created | 2026-08-29T12:42:00Z |
| Updated | 2026-08-29T12:50:00Z |
| Depends on | TASK-007 |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Rounds | 3 |
| Contract tests | `monitoring.contract_tests.test_prometheus_files_contract` |
| Working directory | Repository root |

## Objetivo

Versionar una unidad systemd de ejemplo para node_exporter que escucha sólo en
`127.0.0.1:9100` y usa `/var/lib/node_exporter/textfile_collector`; no instala
ni activa servicios.

## Archivos

- `monitoring/systemd/node-exporter.service`
