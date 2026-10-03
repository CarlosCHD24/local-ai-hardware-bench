# TASK-019: Reconciliar documentación y despliegue

| Campo | Valor |
|---|---|
| Status | `ready` |
| Owner | — |
| Created | 2026-08-29T22:30:00Z |
| Updated | 2026-08-29T22:30:00Z |
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
