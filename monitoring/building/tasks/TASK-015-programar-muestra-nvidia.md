# TASK-015: Programar la muestra NVIDIA

| Campo | Valor |
|---|---|
| Status | `done` |
| Owner | — |
| Created | 2026-08-29T13:10:00Z |
| Updated | 2026-08-29T13:10:00Z |
| Depends on | TASK-007 |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s |
| Rounds | 3 |
| Contract tests | comprobación estática |
| Working directory | Repository root |

## Objetivo

Crear una unidad oneshot que ejecute el adaptador NVIDIA con directorio
`/var/lib/node_exporter/textfile_collector`; no habilita ni ejecuta la unidad.
