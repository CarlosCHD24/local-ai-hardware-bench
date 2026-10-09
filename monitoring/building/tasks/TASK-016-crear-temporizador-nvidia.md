# TASK-016: Crear temporizador NVIDIA

| Campo | Valor |
|---|---|
| Status | `done` |
| Owner | — |
| Created | 2026-08-29T13:10:00Z |
| Updated | 2026-08-29T13:10:00Z |
| Depends on | TASK-015 |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s |
| Rounds | 3 |
| Contract tests | comprobación estática |
| Working directory | Repository root |

## Objetivo

Crear un temporizador systemd que lance TASK-015 cada 15 segundos con retraso
aleatorio nulo y persistencia tras reinicio.
