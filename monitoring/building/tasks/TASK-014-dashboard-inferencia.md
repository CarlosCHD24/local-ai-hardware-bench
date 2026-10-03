# TASK-014: Crear dashboard base de inferencia

| Campo | Valor |
|---|---|
| Status | `done` |
| Owner | — |
| Created | 2026-08-29T13:00:00Z |
| Updated | 2026-08-29T13:00:00Z |
| Depends on | TASK-011 |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s |
| Rounds | 3 |
| Contract tests | comprobación JSON estática |
| Working directory | Repository root |

## Objetivo

Crear un dashboard JSON con paneles de disponibilidad, tokens generados,
rendimiento y caché; no incluye costes ni alertas de umbral.

## Archivos

- `monitoring/grafana/dashboards/inferencia.json`
